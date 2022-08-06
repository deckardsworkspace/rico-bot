from dataclass.custom_embed import CustomEmbed, create_error_embed, create_success_embed
from dataclass.recommendation import Recommendation
from nextcord import Guild, Interaction, slash_command, SlashOption, User
from nextcord.ext import application_checks
from nextcord.ext.commands import Cog
from typing import Optional, TYPE_CHECKING
from util.config import get_debug_guilds
from util.list_util import list_chunks
from util.paginator import Paginator
from util.recommendation_parser import parse_recommendation
if TYPE_CHECKING:
    from util.rico_bot import RicoBot


class RecommendationCog(Cog):
    def __init__(self, bot: 'RicoBot'):
        self._bot = bot
        print(f'Loaded cog: {self.__class__.__name__}')
    
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

    @slash_command(name='list', guild_ids=get_debug_guilds())
    async def list(
        self,
        itx: Interaction,
        list_server: Optional[bool] = SlashOption(
            name='display_server_list',
            description='Display the server\'s list instead of your own',
            required=False,
            default=False
        )
    ):
        """
        Display your list of recommendations.
        """
        await itx.response.defer(ephemeral=not list_server)

        # Get recommendations
        recommendations = []
        if list_server:
            recommendations = self._bot.db.get_guild_recommendations(itx.guild_id)
            if not recommendations:
                return await itx.followup.send(embed=create_error_embed(body='There are no recommendations made to the server.'))
        else:
            recommendations = self._bot.db.get_user_recommendations(itx.user.id)
            if not recommendations:
                return await itx.followup.send(embed=create_error_embed(body='You have no recommendations.'))

        # Create recommendation pages
        pages = []
        for chunk in list_chunks(recommendations, 5):
            fields = []
            item: Recommendation
            for item in chunk:
                fields.append((
                    item.title,
                    '\n'.join([x for x in [
                        item.url,
                        f'added by <@{item.recommender}> <t:{int(item.timestamp.timestamp())}:R>',
                        f'ID `{item.id}`'
                    ] if x])
                ))
            
            # Create embed
            pages.append(CustomEmbed(
                title=f'Recommendations for {itx.guild.name if list_server else itx.user.name}',
                description=f'{len(recommendations)} total',
                fields=fields
            ).get())

        # Run paginator
        paginator = Paginator(itx)
        await paginator.run(pages)
    
    @slash_command(name='remove', guild_ids=get_debug_guilds())
    async def remove(
        self,
        itx: Interaction,
        recommendation_id: Optional[str] = SlashOption(
            name='recommendation_id',
            description='ID of the recommendation to remove (get with `/list`)',
            required=False
        ),
        remove_all: Optional[bool] = SlashOption(
            name='remove_all',
            description='Remove all recommendations. **Warning: irreversible!**',
            required=False,
            default=False
        )
    ):
        """
        Remove a recommendation from your list.
        """
        await itx.response.defer()

        # Check if ID is specified when not removing all
        if not remove_all and recommendation_id is None:
            return await itx.followup.send(embed=create_error_embed(
                body='You must specify a recommendation ID. Check IDs with the `/list` command.'
            ))

        # Remove recommendation
        if remove_all:
            try:
                self._bot.db.remove_all_user_recommendations(itx.user.id)
            except Exception as e:
                return await itx.followup.send(embed=create_error_embed(body=str(e)))
            else:
                return await itx.followup.send(embed=create_success_embed(body='All recommendations removed.'))
        else:
            try:
                self._bot.db.remove_user_recommendation(itx.user.id, recommendation_id)
            except Exception as e:
                return await itx.followup.send(embed=create_error_embed(body=str(e)))
            else:
                return await itx.followup.send(embed=create_success_embed(
                    body=f'Recommendation with ID `{recommendation_id}` removed.'
                ))
    
    @slash_command(name='removefromserver', guild_ids=get_debug_guilds())
    @application_checks.has_guild_permissions(administrator=True)
    async def remove_from_server(
        self,
        itx: Interaction,
        recommendation_id: Optional[str] = SlashOption(
            name='recommendation_id',
            description='ID of the recommendation to remove (get with `/list`)',
            required=False
        ),
        remove_all: Optional[bool] = SlashOption(
            name='remove_all',
            description='Remove all recommendations. **Warning: irreversible!**',
            required=False,
            default=False
        )
    ):
        """
        Remove a recommendation from the server's list.
        """
        await itx.response.defer()

        # Check if ID is specified when not removing all
        if not remove_all and recommendation_id is None:
            return await itx.followup.send(embed=create_error_embed(
                body='You must specify a recommendation ID. Check IDs with the `/list` command.'
            ))

        # Remove recommendation
        if remove_all:
            try:
                self._bot.db.remove_all_guild_recommendations(itx.guild_id)
            except Exception as e:
                return await itx.followup.send(embed=create_error_embed(body=str(e)))
            else:
                return await itx.followup.send(embed=create_success_embed(body='All recommendations removed.'))
        else:
            try:
                self._bot.db.remove_guild_recommendation(itx.guild_id, recommendation_id)
            except Exception as e:
                return await itx.followup.send(embed=create_error_embed(body=str(e)))
            else:
                return await itx.followup.send(embed=create_success_embed(
                    body=f'Recommendation with ID `{recommendation_id}` removed.'
                ))
