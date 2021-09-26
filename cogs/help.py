from nextcord.ext.commands import Bot, Cog, command, Context
from nextcord import Embed
from util import get_var


rec_help_list = {
    '{0}auth': 'Authenticate Rico with your Spotify account. Required to use `{0}dump`.',
    '{0}dump': 'Export all your recommended Spotify tracks to a new Spotify playlist in your library. Does not include artists, albums, or playlists.',
    '{0}clear, {0}c': 'Clear your recommendations.',
    '{0}clearsvr, {0}cs': 'Clear the server recommendations. *Admin only.*',
    '{0}help, {0}h': 'Show this help message.',
    '{0}list, {0}l': 'List all your recommendations.',
    '{0}list @mention': 'List all recommendations for `@mention`.',
    '{0}listsvr, {0}ls': 'List all recommendations for the server.',
    '{0}recommend, {0}r': 'Recommend something to the server.',
    '{0}recommend @mention': 'Recommend something to someone or yourself.',
    '{0}remove, {0}rm': 'Remove a recommendation from your list.',
    '{0}removesvr, {0}rms': 'Remove a recommendation from the server\'s list. *Admin only.*'
}

music_help_list = {
    '{0}clearqueue, {0}cq': 'Clear the playback queue for the server.',
    '{0}disconnect, {0}dc': 'Stop playback, clear the queue, and disconnect from voice.',
    '{0}nowplaying, {0}np': 'Show the currently playing track.',
    '{0}play <URL/search term>, {0}p': 'Play a song, album, or playlist. Supported URLs are YouTube, Spotify, and Twitch.',
    '{0}pause': 'Pause playback.',
    '{0}queue, {0}q': 'Show the current playback queue.',
    '{0}resetplayer, {0}rp': 'Reset the player state for the server.',
    '{0}shuffle, {0}shuf': 'Shuffle the current playback queue.',
    '{0}skip, {0}next': 'Skip currently playing track.',
    '{0}unpause': 'Resume playback.'
}


class Help(Cog):
    def __init__(self, client: Bot):
        self.client = client
    
    @command(name='help', aliases=['h'])
    async def help(self, ctx: Context):
        rec_help = ['**Recommendation commands**']
        cmd_prefix = get_var('BOT_PREFIX')
        for key, value in rec_help_list.items():
            cmd_name = key.format(cmd_prefix)
            cmd_desc = value.format(cmd_prefix)
            rec_help.append('`{0}` - {1}'.format(cmd_name, cmd_desc))
        rec_help = '\n'.join(rec_help)

        music_help = ['**Music commands (alpha - will break!)**']
        for key, value in music_help_list.items():
            cmd_name = key.format(cmd_prefix)
            cmd_desc = value.format(cmd_prefix)
            music_help.append('`{0}` - {1}'.format(cmd_name, cmd_desc))
        music_help = '\n'.join(music_help)

        help_text = '\n\n'.join([rec_help, music_help])
        embed = Embed(title=f'Commands for {self.client.user.name}', description=help_text, color=0x20ce09)
        embed.set_footer(text='Join the official support server at discord.gg/njtK9G6QRG')
        embed.set_thumbnail(url=self.client.user.avatar.url)
        await ctx.reply(embed=embed)
