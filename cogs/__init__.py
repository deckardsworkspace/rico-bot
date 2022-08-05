from .recommendation import Recommendation
from .export import Export
from .help import Help
from .thread import ThreadManager
from nextcord.ext.commands import Bot
from util import Spotify


def setup(bot: Bot):
    # Instantiate Spotipy
    spotify = Spotify()

    # Add cogs
    bot.add_cog(Help(bot))
    bot.add_cog(Export(bot, spotify))
    bot.add_cog(Recommendation(bot, spotify))
    bot.add_cog(ThreadManager(bot))
