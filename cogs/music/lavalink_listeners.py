from asyncio import sleep
from lavalink.events import *
from nextcord.ext.commands import Context


async def track_hook(self, event: Event):
    # Recover context
    guild_id = None
    ctx = None
    if hasattr(event, 'player'):
        ctx = event.player.fetch('context')
        if isinstance(ctx, Context):
            guild_id = str(ctx.guild.id)

    if isinstance(event, TrackStartEvent):
        # Send now playing embed
        track_info = event.track.title
        if hasattr(event.player.current, 'identifier'):
            # Get info currently playing track
            stored_info = event.player.fetch(event.player.current['identifier'])
            if stored_info and 'title' in stored_info:
                track_info = stored_info
        await self.now_playing(ctx, track_info=track_info)

        # Store now playing in DB
        self.db.child('player').child(guild_id).child('np').set(event.track.title)
    elif isinstance(event, TrackEndEvent):
        if event.reason == 'FINISHED':
            # Wait a minute before checking inactivity
            await sleep(60)
            if event.player.is_playing:
                # Still talking, carry on
                return

            # No longer talking, leave voice
            ctx = event.player.fetch('context')
            if isinstance(ctx, Context) and event.player.is_connected:
                await self.disconnect(ctx, reason='Inactive for 1 minute')
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
