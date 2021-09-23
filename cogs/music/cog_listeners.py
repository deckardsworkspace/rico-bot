from asyncio import sleep
from nextcord import Color, Embed, Member, VoiceState
from nextcord.ext.commands import Cog, Context
from util import VoiceCommandError


def cog_unload(self):
    """ Cog unload handler. This removes any event hooks that were registered. """
    self.bot.lavalink._event_hooks.clear()


async def cog_before_invoke(self, ctx: Context):
    """ Command before-invoke handler. """
    # Only allow music commands in guilds
    guild_check = ctx.guild is not None
    if guild_check:
        # Ensure that the bot and command author share a mutual voice channel
        await self.ensure_voice(ctx)
    return guild_check


async def ensure_voice(self, ctx: Context):
    """ This check ensures that the bot and command author are in the same voice channel. """
    # Ensure a player exists for this guild
    player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))

    if not ctx.author.voice or not ctx.author.voice.channel:
        raise VoiceCommandError(':raised_hand: | Join a voice channel first.')

    vc = ctx.author.voice.channel
    if not player.is_connected:
        # Bot needs to already be in voice channel to pause, unpause, skip etc.
        if not ctx.command.name in ('play', 'p', 'resetplayer', 'rp'):
            raise VoiceCommandError(':electric_plug: | I\'m not connected to voice.')

        permissions = vc.permissions_for(ctx.me)
        if not permissions.connect or not permissions.speak:
            raise VoiceCommandError(':mute: | I need the `CONNECT` and `SPEAK` permissions.')
        
        if vc.user_limit and vc.user_limit <= len(vc.members):
            raise VoiceCommandError(':mute: | Your voice channel is full.')

        # Save context for later
        player.store('context', ctx)
    else:
        if int(player.channel_id) != vc.id:
            raise VoiceCommandError(':speaking_head: | You need to be in my voice channel.')


@Cog.listener()
async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
    # Ignore events not triggered by this bot
    if not member.id == self.bot.user.id:
        return
    
    # Ignore leave events
    if after.channel is not None:
        # Get the player for this guild from cache
        guild_id = after.channel.guild.id
        player = self.bot.lavalink.player_manager.get(guild_id)

        # Deafen this bot
        if not after.deaf:
            await member.edit(deafen=True)
            if before.deaf:
                # Someone undeafened me!
                ctx = player.fetch('context')
                if isinstance(ctx, Context):
                    embed = Embed(color=Color.red())
                    embed.title = 'Deafened the bot'
                    embed.description = 'Please don\'t undeafen me! This helps me save resources.'
                    await ctx.send(embed=embed)

        # Join events
        if before.channel is None:
            # Deafen this bot
            await member.edit(deafen=True)

            while True:
                # Wait a minute before checking inactivity
                await sleep(60)
                if player.is_playing and not player.paused:
                    # Still talking, carry on
                    continue

                # No longer talking, leave voice
                ctx = player.fetch('context')
                if isinstance(ctx, Context) and player.is_connected:
                    await self.disconnect(ctx, reason='Inactive for 1 minute')
                return
