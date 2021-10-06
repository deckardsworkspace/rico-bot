from nextcord.ext.commands import Bot, Cog, command, Context
from nextcord import Color, Embed
from typing import Union
from util import get_var


help_list = {
    'rec': {
        'title': 'Recommendation commands',
        'commands': {
            '{0}clear, {0}c': 'Clear your recommendations.',
            '{0}clearsvr, {0}cs': 'Clear the server recommendations. *Admin only.*',
            '{0}help, {0}h': 'Show this help message.',
            '{0}list, {0}l': 'List all your recommendations.',
            '{0}list @mention': 'List all recommendations for `@mention`.',
            '{0}listsvr, {0}ls': 'List all recommendations for the server.',
            '{0}recommend, {0}r': 'Recommend something to the server.',
            '{0}recommend @mention': 'Recommend something to someone or yourself.',
            '{0}rectext, {0}rt': 'Add a text entry to the server\'s recommendations.',
            '{0}rectext @mention': 'Add a text entry to your or someone\'s recommendations.',
            '{0}remove, {0}rm': 'Remove a recommendation from your list.',
            '{0}removesvr, {0}rms': 'Remove a recommendation from the server\'s list. *Admin only.*'
        }
    },
    'export': {
        'title': 'Spotify export commands',
        'commands': {
            '{0}auth, {0}login': 'Authenticate Rico with your Spotify account. Required to use `{0}dump`.',
            '{0}deauth, {0}logout': 'Deauthenticate Rico from your Spotify account. You will still have to remove Rico yourself from your Spotify account settings.',
            '{0}dump': 'Export all your recommended Spotify tracks to a new Spotify playlist in your library. Does not include artists, albums, or playlists.',
        }
    },
    'music': {
        'title': 'Music player commands (alpha - will break!)',
        'commands': {
            '{0}clearqueue, {0}cq': 'Clear the playback queue for the server.',
            '{0}disconnect, {0}dc': 'Stop playback, clear the queue, and disconnect from voice.',
            '{0}nowplaying, {0}np': 'Show the currently playing track.',
            '{0}play <URL/search term>, {0}p': 'Play a song, album, or playlist. Supports YouTube, Spotify, and Twitch URLs.',
            '{0}pause': 'Pause playback.',
            '{0}queue, {0}q': 'Show the current playback queue.',
            '{0}recnow, {0}rn': 'Recommend the currently playing track to the server.',
            '{0}recnow @mention': 'Recommend the currently playing track to someone or yourself.',
            '{0}removequeue <num/nums>, {0}rmq': 'Remove the specified songs from the queue, i.e. `{0}rmq 2 3` to dequeue songs 2 and 3.',
            '{0}resetplayer, {0}rp': 'Reset the player state for the server.',
            '{0}shuffle, {0}shuf': 'Shuffle the current playback queue.',
            '{0}skip, {0}next': 'Skip currently playing track.',
            '{0}unpause': 'Resume playback.',
            '{0}volume, {0}v, {0}vol': 'Adjust player volume.'
        }
    },
    'thread': {
        'title': 'Thread management commands (admin only)',
        'commands': {
            '{0}tte': 'Toggle exclusion for a thread. If excluded, the thread will be archived automatically after inactivity.',
            '{0}ttm': 'Toggle thread monitoring for this server. If monitored, all threads will be kept unarchived.'
        }
    }
}


class Help(Cog):
    def __init__(self, client: Bot):
        self.client = client
        print('Loaded cog: Help')
    
    @command(name='help', aliases=['h'])
    async def help(self, ctx: Context, *, query: Union[str, int] = None):
        valid_keys = list(help_list.keys())
        cmd_prefix = get_var('BOT_PREFIX')
        embed = Embed(color=Color.og_blurple())
        embed.set_footer(text='Join the official support server at discord.gg/njtK9G6QRG')
        embed.set_thumbnail(url=self.client.user.avatar.url)

        if query is None:
            # Display available help categories
            embed.title = f'Help for {ctx.guild.me.nick}'

            for key, value in help_list.items():
                key_idx = valid_keys.index(key)
                invoked_cmd = f'{cmd_prefix}{ctx.invoked_with}'
                field_name = f'`{invoked_cmd} {key}`, `{invoked_cmd} {key_idx}`'
                embed.add_field(name=field_name, value=value, inline=False)

            return await ctx.reply(embed=embed)
        
        try:
            key_idx = int(query) - 1
            
            if key_idx >= len(valid_keys):
                embed.title = f'Invalid help index "{query}"'
                embed.description = f'Valid indices are from 1 to {len(valid_keys)}'
                return await ctx.reply(embed=embed)

            query = valid_keys[key_idx]
        except ValueError:
            # Not an integer query
            pass

        if query in valid_keys:
            # Display help category
            help_category = help_list[query]
            embed.title = help_category["title"]

            help_cat_text = []
            for key, value in help_category['commands'].items():
                cmd_name = key.format(cmd_prefix)
                cmd_desc = value.format(cmd_prefix)
                help_cat_text.append('`{0}` - {1}'.format(cmd_name, cmd_desc))

            embed.description = '\n'.join(help_cat_text)
            return await ctx.reply(embed=embed)
        
        # Invalid key
        embed.title = f'Invalid help key "{query}"'
        embed.description = f'Valid keys: `{", ".join(valid_keys)}`'
        return await ctx.reply(embed=embed)
