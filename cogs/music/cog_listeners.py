from asyncio import sleep
from nextcord import Member, VoiceState
from nextcord.ext.commands import Bot, Cog, Context
from util import VoiceCommandError


async def ensure_voice(bot: Bot, ctx: Context):
    """ This check ensures that the bot and command author are in the same voice channel. """
    # Ensure a player exists for this guild
    player = bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))

    if not ctx.author.voice or not ctx.author.voice.channel:
        raise VoiceCommandError(':raised_hand: | Join a voice channel first.')

    vc = ctx.author.voice.channel
    if not player.is_connected:
        # Bot needs to already be in voice channel to pause, unpause, skip etc.
        if ctx.command.name not in ('play', 'p', 'resetplayer', 'rp'):
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
        ctx = player.fetch('context')

        # Join events
        if before.channel is None:
            # Inactivity check
            time = 0
            while True:
                await sleep(1)
                time = time + 1

                if player is not None:
                    if player.is_playing and not player.paused:
                        time = 0
                    if time == 60:
                        await self.disconnect(ctx, reason='Inactive for 1 minute')
                    if not player.is_connected:
                        break
