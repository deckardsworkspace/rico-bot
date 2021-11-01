from nextcord.ext.commands import command, guild_only
from .recommend_db import get_recommendations


@command(name='list', aliases=['l'])
async def list_personal(self, ctx):
    """
    List stuff recommended to you or other people.

    To see other people's lists, mention them after the command.
    e.g. rc!list @someone
    """
    if not len(ctx.message.mentions):
        await get_recommendations(ctx, self.client, self.db, ctx.author.name, ctx.author.avatar.url,
                                  server=False, entity_id=str(ctx.author.id))
    else:
        user = ctx.message.mentions[0]
        await get_recommendations(ctx, self.client, self.db, user.name, user.avatar.url, server=False, entity_id=str(user.id))


@guild_only()
@command(name='listsvr', aliases=['ls', 'svrlist'])
async def list_guild(self, ctx):
    """List stuff recommended to everyone on the server."""
    await get_recommendations(ctx, self.client, self.db, ctx.guild.name, ctx.guild.icon.url, server=True)
