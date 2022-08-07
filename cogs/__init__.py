from nextcord.ext.commands import Bot
from .export import ExportCog
from .recommendation import RecommendationCog
from .thread import ThreadsCog


def setup(bot: Bot):
    # Add cogs
    bot.add_cog(ExportCog(bot))
    bot.add_cog(RecommendationCog(bot))
    bot.add_cog(ThreadsCog(bot))

    # Sync slash commands
    bot.loop.create_task(bot.sync_all_application_commands())
