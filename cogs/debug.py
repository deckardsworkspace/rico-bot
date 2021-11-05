import distro
import ipaddress
import os
import platform
import subprocess
from datetime import datetime
from nextcord import Color
from nextcord.ext.commands import Bot, Cog, command, is_owner, Context
from util import check_ip_addr, human_readable_size, human_readable_time
from util.message_util import MusicEmbed


def check_local_ip(host: str) -> bool:
    """
    Check if the host is local.
    """
    local_nets = [
        ipaddress.ip_network('192.168.0.0/24'),
        ipaddress.ip_network('172.16.0.0/12'),
        ipaddress.ip_network('10.0.0.0/8')
    ]
    for net in local_nets:
        try:
            if ipaddress.ip_address(host) in net:
                return True
        except ValueError:
            # Invalid IP address
            return False
    return False


# Debugging cog
class Debug(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        print('Loaded debug cog')
    
    @command(aliases=['i'])
    async def info(self, ctx: Context):
        info = []

        # Get Git commit
        commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode()
        commit_date = subprocess.check_output(['git', 'show', '-s', '--format=%cd', '--date=short']).strip().decode()
        tree_url = f'https://github.com/jareddantis/rico-bot/tree/{commit_hash}'

        # Count users
        guilds = self.bot.guilds
        users = 0
        for guild in guilds:
            users += guild.member_count
        info.append([
            '__**Bot info**__',
            '\n'.join([
                f'Logged in as **{self.bot.user.name}#{self.bot.user.discriminator}**',
                f'Latency to Discord is `{(self.bot.latency * 1000):.02f} ms`',
                f'Listening to **{users}** users across **{len(guilds)}** servers',
                f'Version `{commit_hash[:7]}` [**({commit_date})**]({tree_url})'
            ])
        ])

        # Display server info
        server_os = platform.system()
        if server_os == 'Linux':
            # Display Linux distribution
            server_os = distro.name(pretty=True)
        info.append([
            '__**Bot environment**__',
            '\n'.join([
                f'Python version `{platform.python_version()}` on `{server_os}`',
                f'running on `{os.cpu_count()}x {platform.processor()}` CPUs'
            ])
        ])

        # Display Lavalink node info
        if hasattr(self.bot, 'lavalink'):
            nodes_info = []
            nodes = self.bot.lavalink.node_manager.available_nodes
            for i, node in enumerate(nodes):
                node_name = node.name
                if check_ip_addr(node.host) and check_local_ip(node.host):
                    node_name = f'{node.host} (local)'
                
                node_uptime_h, node_uptime_m, node_uptime_s = human_readable_time(node.stats.uptime)
                node_uptime_d, node_uptime_h = divmod(node_uptime_h, 24)
                node_load = node.stats.lavalink_load * 100
                node_stats = '\n'.join([
                    f'Node #       :: {i + 1}',
                    f'Host         :: {node_name}',
                    f'Connected    :: {node.available}',
                    f'Players      :: {node.stats.playing_players} playing out of {node.stats.players} total',
                    f'CPU usage    :: {node_load:.2f}% across {node.stats.cpu_cores} core(s)',
                    f'Memory usage :: {human_readable_size(node.stats.memory_used)}',
                    f'Uptime       :: {node_uptime_d:.0f} days, {node_uptime_h:.0f}:{node_uptime_m:.0f}:{node_uptime_s:.0f}'
                ])
                nodes_info.append(f'```asciidoc\n{node_stats}```')
            
            if not len(nodes_info):
                nodes_info = [':warning: No nodes available! Bot cannot play music.']
            info.append(['__**Lavalink node status**__', '\n'.join(nodes_info)])

        # Build and send embed
        embed = MusicEmbed(
            header=f'Info for {ctx.guild.me.display_name}',
            thumbnail_url=self.bot.user.avatar.url,
            color=Color.green(),
            description='\n\n'.join(['\n'.join(i) for i in info]),
            footer=f'Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        )
        return await embed.send(ctx=ctx, as_reply=True)
    
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
