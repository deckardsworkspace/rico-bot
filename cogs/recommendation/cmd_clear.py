from nextcord.ext.commands import command, guild_only
from util import is_int
from .recommend_db import create_remove_dialog, remove_recommendation


@command(aliases=['clr', 'c'])
async def clear(self, ctx):
    """Clear your recommendations."""
    if await create_remove_dialog(self.client, ctx, server=False):
        self.db.child("recommendations").child("user").child(str(ctx.author.id)).remove()
        await ctx.reply("Cleared your recommendations.")


@guild_only()
@command(name='clearsvr', aliases=['clrsvr', 'cs'])
async def clear_guild(self, ctx):
    """
    Clear the server recommendations.
    Only a member with the Administrator permission can issue this command.
    """
    if ctx.author.guild_permissions.administrator:
        if await create_remove_dialog(self.client, ctx, server=True):
            self.db.child("recommendations").child("server").child(str(ctx.guild.id)).remove()
            await ctx.reply("Cleared server recommendations.")
    else:
        await ctx.reply("Only administrators can clear server recommendations.")


@command(aliases=['rm', 'del'])
async def remove(self, ctx, *args):
    """
    Remove a recommendation from your list.
    To use, type rc!remove <index>, where <index> is the number of the recommendation
    you wish to remove, as listed by rc!list.
    """
    if len(args) and is_int(args[0]):
        await remove_recommendation(self.client, self.db, ctx, int(args[0]))
    else:
        await ctx.reply("Invalid or missing index.")


@guild_only()
@command(name='removesvr', aliases=['rms', 'dels'])
async def remove_guild(self, ctx, *args):
    """
    Remove a recommendation from the server's list.
    To use, type rc!remove <index>, where <index> is the number of the recommendation
    you wish to remove, as listed by rc!listsvr.
    """
    if ctx.author.guild_permissions.administrator:
        if len(args) and is_int(args[0]):
            await remove_recommendation(self.client, self.db, ctx, int(args[0]), server=True)
        else:
            await ctx.reply("Invalid or missing index.")
    else:
        await ctx.reply("Only administrators can remove server recommendations.")
