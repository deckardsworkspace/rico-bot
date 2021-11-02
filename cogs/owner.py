from nextcord.ext.commands import Bot, Cog, command, is_owner, Context


# Owner-only cog
class Owner(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        print('Loaded owner-only cog')
    
    @command(name='reload')
    @is_owner()
    async def reload_cogs(self, ctx: Context):
        try:
            self.bot.unload_extension('cogs')
            self.bot.load_extension('cogs')
        except Exception as e:
            await ctx.reply(f'Failed to reload cogs. {type(e).__name__}: {e}')
        else:
            await ctx.reply('Reloaded cogs.')
