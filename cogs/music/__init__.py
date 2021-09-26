from lavalink import add_event_hook, Client as LavalinkClient
from lavalink.events import *
from nextcord.ext.commands import Bot, Cog, Context
from util import get_var, Spotify
from .cog_listeners import ensure_voice


class Music(Cog):
    """ Based on https://github.com/Devoxin/Lavalink.py/blob/master/examples/music.py """
    def __init__(self, bot: Bot, db, spotify: Spotify):
        self.bot = bot
        self.db = db
        self.spotify = spotify

        # This ensures the client isn't overwritten during cog reloads
        if not hasattr(bot, 'lavalink'):
            bot.lavalink = LavalinkClient(bot.user.id)
            bot.lavalink.add_node(
                get_var('LAVALINK_SERVER'),
                get_var('LAVALINK_PORT'),
                get_var('LAVALINK_PASSWORD'),
                'ph', 'default-node'
            )

        # Listen to Lavalink events
        add_event_hook(self.on_lavalink_event)

    # Event listeners
    from .cog_listeners import on_voice_state_update

    async def cog_before_invoke(self, ctx: Context):
        """ Command before-invoke handler. """
        # Only allow music commands in guilds
        guild_check = ctx.guild is not None
        if guild_check:
            # Ensure that the bot and command author share a mutual voice channel
            await ensure_voice(self.bot, ctx)
        return guild_check

    def cog_unload(self):
        """ Cog unload handler. This removes any event hooks that were registered. """
        if hasattr(self.bot, 'lavalink'):
            self.bot.lavalink._event_hooks.clear()

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
            await self.skip(ctx, queue_end=True)

    # Commands
    from .cmd_player import now_playing, pause, play, skip, unpause
    from .cmd_queue import clear_queue, queue, shuffle
    from .cmd_stop import disconnect, reset_player
