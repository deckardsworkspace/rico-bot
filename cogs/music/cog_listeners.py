from asyncio import sleep
from lavalink.exceptions import NodeException
from nextcord import Member, VoiceState
from nextcord.ext.commands import Bot, Cog, Context
from util import get_var, human_readable_time, VoiceCommandError


async def cog_before_invoke(self, ctx: Context):
    """ Command before-invoke handler. """
    guild_check = ctx.guild is not None
    if guild_check:
        # Ensure that the bot and command author share a mutual voice channel
        await ensure_voice(self.bot, ctx)
    else:
        # Not allowed!
        await ctx.reply('You can only use this command in a server.')
    return guild_check


def cog_unload(self):
    """ Cog unload handler. This removes any event hooks that were registered. """
    if hasattr(self.bot, 'lavalink'):
        self.bot.lavalink._event_hooks.clear()


async def ensure_voice(bot: Bot, ctx: Context):
    """ This check ensures that the bot and command author are in the same voice channel. """
    # Ensure a player exists for this guild
    try:
        player = bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
    except NodeException:
        if ctx.command.name in ('play', 'p'):
            raise VoiceCommandError('No audio servers currently available. Please try again later.')

    if not ctx.author.voice or not ctx.author.voice.channel:
        raise VoiceCommandError('Join a voice channel first.')

    vc = ctx.author.voice.channel
    if not player.is_connected:
        # Bot needs to already be in voice channel to pause, unpause, skip etc.
        if ctx.command.name not in ('play', 'p', 'resetplayer', 'rp'):
            raise VoiceCommandError('I\'m not connected to voice.')

        permissions = vc.permissions_for(ctx.me)
        if not permissions.connect or not permissions.speak:
            raise VoiceCommandError('I need the `CONNECT` and `SPEAK` permissions to play music.')

        if vc.user_limit and vc.user_limit <= len(vc.members):
            raise VoiceCommandError('Your voice channel is full.')

        # Save context for later
        player.store('context', ctx)
    else:
        if int(player.channel_id) != vc.id:
            raise VoiceCommandError('You need to be in my voice channel.')


@Cog.listener()
async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
    # Stop playing if we're left alone
    if (after.channel is None and len(before.channel.members) == 1 and
        before.channel.members[0].id == self.bot.user.id and not member.id == self.bot.user.id):
        # Get the player for this guild from cache
        guild_id = before.channel.guild.id
        player = self.bot.lavalink.player_manager.get(guild_id)
        ctx = player.fetch('context')
        return await self.disconnect(ctx, reason='You left me alone :(')

    # Only handle join events by this bot
    if before.channel is None and after.channel is not None and member.id == self.bot.user.id:
        # Get the player for this guild from cache
        guild_id = after.channel.guild.id
        player = self.bot.lavalink.player_manager.get(guild_id)
        ctx = player.fetch('context')

        # Inactivity check
        time = 0
        inactive_sec = int(get_var('INACTIVE_SEC'))
        inactive_h, inactive_m, inactive_s = human_readable_time(inactive_sec * 1000)
        inactive_h = f'{inactive_h}h ' if inactive_h else ''
        inactive_m = f'{inactive_m}m ' if inactive_m else ''
        inactive_s = f'{inactive_s}s' if inactive_s else ''
        while True:
            await sleep(1)
            time = time + 1

            if player is not None:
                if player.is_playing and not player.paused:
                    time = 0
                # TODO: Turn this into an environment variable
                if time == inactive_sec:
                    await self.disconnect(ctx, reason=f'Inactive for {inactive_h}{inactive_m}{inactive_s}')
                if not player.is_connected:
                    break
