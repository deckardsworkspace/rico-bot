from dataclass.custom_embed import create_error_embed, create_success_embed
from nextcord import Guild, Interaction, slash_command, SlashOption, User
from nextcord.ext import application_checks
from nextcord.ext.commands import Cog
from typing import Optional, TYPE_CHECKING
from util.config import get_debug_guilds
from util.recommendation_parser import parse_recommendation
if TYPE_CHECKING:
    from util.rico_bot import RicoBot


class RecommendationCog(Cog):
    def __init__(self, bot: 'RicoBot'):
        self._bot = bot
    
    def _ensure_records(self, guild: Optional[Guild] = None, user: Optional[User] = None):
        if guild:
            self._bot.db.update_guild(guild.id, guild.name)
        if user:
            self._bot.db.update_user(user.id, user.name, user.discriminator)

    @slash_command(name='recommend', guild_ids=get_debug_guilds())
    @application_checks.guild_only()
    async def recommend(
        self,
        itx: Interaction,
        url_or_text: str = SlashOption(
            name='recommendation',
            description='URL or text to add to their list',
            required=True
        ),
        recommendee: Optional[User] = SlashOption(
            name='recipient',
            description='User to add the recommendation to. Leave blank to add to the server\'s list.',
            required=False
        )):
        """
        Add something to someone's or the server's list.
        """
        await itx.response.defer()

        # Create Recommendation
        recommender = itx.user.id
        self._ensure_records(guild=itx.guild, user=itx.user)
        if recommendee is None:
            # Add recommendation to server's list
            recommendation = parse_recommendation(self._bot.spotify, url_or_text, recommender, itx.guild_id)
            self._bot.db.add_guild_recommendation(itx.guild_id, recommendation)
            await itx.followup.send(embed=create_success_embed(
                title='Recommendation added',
                body=f'**{recommendation.title}** added to this server\'s list.'
            ))
        else:
            # Add recommendation to user's list
            self._ensure_records(user=recommendee)
            recommendation = parse_recommendation(self._bot.spotify, url_or_text, recommender, recommendee.id)
            self._bot.db.add_user_recommendation(recommendee.id, recommendation)
            await itx.followup.send(embed=create_success_embed(
                title='Recommendation added',
                body=f'**{recommendation.title}** added to {recommendee.mention}\'s list.'
            ))
