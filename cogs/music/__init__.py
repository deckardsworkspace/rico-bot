from lavalink import add_event_hook
from lavalink.events import *
from nextcord.ext.commands import Bot, Cog, Context
from util import Spotify
from .lavalink import init_lavalink


class Music(Cog):
    """ Based on https://github.com/Devoxin/Lavalink.py/blob/master/examples/music.py """
    def __init__(self, bot: Bot, db, spotify: Spotify):
        self.bot = bot
        self.db = db
        self.spotify = spotify

        # This ensures the client isn't overwritten during cog reloads
        if not hasattr(bot, 'lavalink'):
            bot.lavalink = init_lavalink(bot.user.id)

        # Listen to Lavalink events
        add_event_hook(self.on_lavalink_event)

        print('Loaded cog: Music')

    # Event listeners
    from .cog_listeners import cog_before_invoke, cog_unload, on_voice_state_update

    async def on_lavalink_event(self, event: Event):
        # Recover context
        guild_id = None
        ctx = None
        if hasattr(event, 'player'):
            guild_id = str(event.player.guild_id)
            ctx = event.player.fetch('context')
            if not isinstance(ctx, Context):
                raise RuntimeError(f'Could not recover Context object from player for guild {guild_id}')

        if isinstance(event, TrackStartEvent):
            # Send now playing embed
            track_info = event.player.current
            if hasattr(track_info, 'identifier'):
                # Get info currently playing track
                stored_info = event.player.fetch(track_info['identifier'])
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
            await self.skip(ctx, queue_end=True)
    
    def get_player(self, guild_id: int):
        return self.bot.lavalink.player_manager.get(guild_id)

    # Commands
    from .cmd_player import jump_to, loop, now_playing, pause, play, skip, unpause, volume
    from .cmd_queue import clear_queue, move, queue, remove_from_queue, shuffle, unshuffle
    from .cmd_rec import recommend_now_playing
    from .cmd_stop import disconnect, reset_player
