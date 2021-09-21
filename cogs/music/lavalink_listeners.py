from lavalink.events import *
from nextcord.ext.commands import Context


async def track_hook(self, event):
    # Recover context
    guild_id = None
    ctx = None
    if hasattr(event, 'player'):
        ctx = event.player.fetch('context')
        if isinstance(ctx, Context):
            guild_id = str(ctx.guild.id)

    if isinstance(event, TrackStartEvent):
        # Send now playing embed
        await self.now_playing(ctx, title=event.track.title)

        # Store now playing in DB
        self.db.child('player').child(guild_id).child('np').set(event.track.title)
    elif isinstance(event, QueueEndEvent):
        # Queue up the next (valid) track from DB, if any
        queue = self.get_queue_db(guild_id)
        while len(queue):
            if await self.enqueue(queue.popleft(), event.player, ctx=ctx, queue_to_db=False, quiet=True):
                break
        else:
            await self.disconnect(ctx, reason='Queue finished')

        # Save new queue back to DB
        self.set_queue_db(guild_id, queue)
