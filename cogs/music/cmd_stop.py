from collections import deque
from nextcord import Color, Embed
from nextcord.ext.commands import command, Context
from .queue_helpers import set_queue_db


@command(aliases=['stop', 'dc'])
async def disconnect(self, ctx: Context, reason: str = None):
    """ Disconnects the player from the voice channel and clears its queue. """
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)

    if reason is None:
        if not player.is_connected:
            # We can't disconnect, if we're not connected.
            return await ctx.reply('Not connected.')

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not disconnect the bot.
            return await ctx.reply('You\'re not in my voice channel!')

        # Clear the queue to ensure old tracks don't start playing
        # when someone else queues something.
        set_queue_db(self.db, str(ctx.guild.id), deque([]))

    # Stop the current track so Lavalink consumes less resources.
    await player.stop()

    # Disconnect from the voice channel.
    if hasattr(ctx.voice_client, 'disconnect'):
        await ctx.voice_client.disconnect(force=True)
    embed = Embed(color=Color.blurple())
    embed.title = 'Disconnected from voice'
    embed.description = reason if reason is not None else 'Stopped the player'
    await ctx.send(embed=embed)


@command(name='resetplayer', aliases=['rp'])
async def reset_player(self, ctx: Context):
    # Delete all traces of the player for this guild from DB
    self.db.child('player').child(str(ctx.guild.id)).remove()
    return await self.disconnect(ctx, reason=f'Reset player state for {ctx.guild.name}')
