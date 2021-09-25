from lavalink.events import *
from lavalink.models import AudioTrack
from nextcord.ext.commands import Context


async def track_hook(self, event: Event):
    # Recover context
    guild_id = None
    ctx = None
    if hasattr(event, 'player'):
        guild_id = str(event.player.guild_id)
        ctx = event.player.fetch('context')
        if not isinstance(ctx, Context):
            raise RuntimeError(f'Could not recover Context object from player for guild {guild_id}')

    if isinstance(event, TrackStartEvent):
        # Mute self
        bot_member = await ctx.guild.fetch_member(self.bot.user.id)
        await bot_member.edit(deafen=True)

        # Send now playing embed
        track_info = event.track.title
        if hasattr(event.player.current, 'identifier'):
            # Get info currently playing track
            stored_info = event.player.fetch(event.player.current['identifier'])
            if stored_info and 'title' in stored_info:
                track_info = stored_info
        await self.now_playing(ctx, track_info=track_info)

        # Store now playing in DB
        self.db.child('player').child(guild_id).child('np').set(event.track.track)
    elif isinstance(event, TrackEndEvent):
        # Delete track metadata from player storage
        if hasattr(event.track, 'identifier'):
            event.player.delete(event.track.identifier)
    elif isinstance(event, QueueEndEvent):
        # Queue up the next (valid) track from DB, if any
        await self.skip(ctx)
