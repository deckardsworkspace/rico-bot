from .recommendation import Recommendation
from .export import Export
from .help import Help
from .music import Music
from .thread import ThreadManager
from nextcord.ext.commands import Bot
from util import get_var, get_pyrebase_config, Spotify
import pyrebase


def setup(bot: Bot):
    # Instantiate Spotipy
    spotify = Spotify()

    # Instantiate Pyrebase
    firebase = pyrebase.initialize_app(get_pyrebase_config())
    db = firebase.database()

    # Add cogs
    bot.add_cog(Help(bot))
    bot.add_cog(Export(bot, db, spotify))
    bot.add_cog(Recommendation(bot, db, spotify, get_var('FIREBASE_KEY')))
    bot.add_cog(ThreadManager(bot, db))

    # Conditional cogs
    if get_var('ENABLE_MUSIC') == '1':
        bot.add_cog(Music(bot, db, spotify))
