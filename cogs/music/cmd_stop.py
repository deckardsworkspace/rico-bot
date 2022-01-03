from nextcord import Color
from nextcord.ext.commands import command, Context
from util import RicoEmbed
from .queue_helpers import set_loop_all


@command(aliases=['stop', 'dc'])
async def disconnect(self, ctx: Context, reason: str = None):
    """ Disconnects the player from the voice channel and clears its queue. """
    player = self.get_player(ctx.guild.id)

    # Don't loop future queues by default
    set_loop_all(self.db, str(ctx.guild.id), False)

    if reason is None:
        # Clear the queue to ensure old tracks don't start playing
        # when someone else queues something.
        self.db.child('player').child(str(ctx.guild.id)).remove()
        player.queue.clear()

    # Stop the current track
    await player.stop()

    # Disconnect from the voice channel
    if hasattr(ctx.voice_client, 'disconnect'):
        await ctx.voice_client.disconnect(force=True)
    
    # Destroy the player
    await self.bot.lavalink.player_manager.destroy(ctx.guild.id)

    embed = RicoEmbed(
        color=Color.blurple(),
        title=':wave:｜Disconnected from voice',
        description=reason if reason is not None else 'Stopped the player',
        timestamp_now=True
    )
    return await embed.send(ctx)


@command(name='resetplayer', aliases=['rp'])
async def reset_player(self, ctx: Context):
    # Delete all traces of the player for this guild from DB
    self.db.child('player').child(str(ctx.guild.id)).remove()
    return await self.disconnect(ctx, reason=f'Reset player state for {ctx.guild.name}')
