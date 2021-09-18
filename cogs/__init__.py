from .recommendation import Recommendation
from .export import Export
from .help import Help
from .music import Music
from nextcord.ext.commands import Bot
from config import get_var, get_pyrebase_config
from util import Spotify
import pyrebase


def setup(bot: Bot):
    # Instantiate Spotipy
    spotify = Spotify()

    # Instantiate Pyrebase
    firebase = pyrebase.initialize_app(get_pyrebase_config())
    auth = firebase.auth()
    db = firebase.database()

    # Add cogs
    bot.add_cog(Export(bot, db, spotify))
    bot.add_cog(Help(bot))
    bot.add_cog(Music(bot))
    bot.add_cog(Recommendation(bot, db, spotify, get_var('FIREBASE_KEY')))
