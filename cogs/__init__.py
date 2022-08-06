from .recommendation import RecommendationCog
from nextcord.ext.commands import Bot


def setup(bot: Bot):
    # Add cogs
    bot.add_cog(RecommendationCog(bot))

    # Sync slash commands
    bot.loop.create_task(bot.sync_all_application_commands())
