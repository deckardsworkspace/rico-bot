from nextcord.ext.commands import Bot, Cog, command, Context
from nextcord import Embed


help_list = {
    '{0}auth': 'Authenticate Rico with your Spotify account. Required to use `{0}dump`.',
    '{0}dump': 'Export all your recommended Spotify tracks to a new Spotify playlist in your library. Does not include artists, albums, or playlists.',
    '{0}clear, {0}c': 'Clear your recommendations.',
    '{0}clearsvr, {0}cs': 'Clear the server recommendations. Admin only.',
    '{0}help, {0}h': 'Show this help message.',
    '{0}list, {0}l': 'List all your recommendations.',
    '{0}list @mention': 'List all recommendations for @mention.',
    '{0}listsvr, {0}ls': 'List all recommendations for the server.',
    '{0}recommend, {0}r': 'Recommend something to the server.',
    '{0}recommend @mention': 'Recommend something to someone or yourself.',
    '{0}remove, {0}rm': 'Remove a recommendation from your list.',
    '{0}removesvr, {0}rms': 'Remove a recommendation from the server\'s list.',
    '{0}select, {0}recselect, {0}rs': 'Select a recommendation from the results of `{0}recommend`.'
}


class Help(Cog):
    def __init__(self, client: Bot):
        self.client = client
    
    @command(name='help', aliases=['h'])
    async def help(self, ctx: Context):
        description = []
        for key, value in help_list.items():
            cmd_name = key.format('rc!')
            cmd_desc = value.format('rc!')
            description.append('`{0}` - {1}'.format(cmd_name, cmd_desc))
        
        embed = Embed(title=f'Commands for {self.client.user.name}', description='\n'.join(description), color=0x20ce09)
        embed.set_footer(text='Join the official support server at https://discord.gg/njtK9G6QRG')
        await ctx.reply(embed=embed)
