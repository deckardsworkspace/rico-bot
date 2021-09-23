from lavalink import add_event_hook, Client as LavalinkClient
from nextcord.ext.commands import Bot, Cog
from util import get_var, Spotify


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
        add_event_hook(self.track_hook)

    # Queue helpers
    from .queue_helpers import enqueue_db
    from .queue_helpers import dequeue_db
    from .queue_helpers import get_queue_db
    from .queue_helpers import set_queue_db

    # Cog event listeners
    from .cog_listeners import cog_before_invoke, cog_unload, ensure_voice
    from .cog_listeners import on_voice_state_update

    # Lavalink event listeners
    from .lavalink_listeners import track_hook

    ################
    ### Commands ###
    ################

    # Player commands
    from .cmd_player import now_playing, pause, play, skip, unpause

    # Queue commands
    from .cmd_queue import clear_queue, enqueue, queue, shuffle

    # Player reset commands
    from .cmd_stop import disconnect, reset_player
