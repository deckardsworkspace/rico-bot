import distro
import ipaddress
import os
import platform
import psutil
import subprocess
from nextcord import Color
from nextcord.ext.commands import Bot, BucketType, Cog, command, Context, cooldown, is_owner
from time import time
from util import human_readable_size, human_readable_time, RicoEmbed


def check_local_host(host: str) -> bool:
    """
    Check if the host is local.
    """
    if host in ('localhost', '0.0.0.0', '127.0.0.1', '::1'):
        return True

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
    @cooldown(1, 2, BucketType.default)
    async def info(self, ctx: Context):
        info = []

        # Count users
        guilds = self.bot.guilds
        users = 0
        for guild in guilds:
            # Don't count the bot!
            users += guild.member_count - 1
        
        # Calculate uptime
        time_now = time()
        bot_process = psutil.Process(os.getpid())
        h, m, s = human_readable_time((time_now - bot_process.create_time()) * 1000)
        d, h = divmod(h, 24)
        info.append([
            '__**Bot info**__',
            '\n'.join([
                f'Logged in as `{self.bot.user.name}#{self.bot.user.discriminator}`',
                f'Listening to `{users}` users across `{len(guilds)}` servers',
                f'Latency to Discord is `{(self.bot.latency * 1000):.02f} ms`',
                f'Online for {d:.0f} days, {h:.0f}:{str(m).zfill(2)}:{str(s).zfill(2)}'
            ])
        ])

        # Display server info
        h, m, s = human_readable_time((time_now - psutil.boot_time()) * 1000)
        d, h = divmod(h, 24)
        server_os = platform.system()
        server_mem = human_readable_size(psutil.virtual_memory().total)
        if server_os == 'Linux':
            # Display Linux distribution
            server_os = distro.name(pretty=True)
        info.append([
            '__**Bot server**__',
            '\n'.join([
                f'Python version `{platform.python_version()}`',
                f'Installed on `{server_os}`',
                f'`{os.cpu_count()}` CPUs and `{server_mem}` RAM available',
                f'Server up for {d:.0f} days, {h:.0f}:{str(m).zfill(2)}:{str(s).zfill(2)}'
            ])
        ])

        # Get Git commit
        try:
            commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode()
            commit_date = subprocess.check_output(['git', 'show', '-s', '--format=%cd', '--date=short']).strip().decode()
            version = f'{commit_date.replace("-", "")}-{commit_hash[:7]}'
            repo_url = f'https://github.com/jareddantis/rico-bot/tree/{commit_hash}'
        except:
            if 'HEROKU_SLUG_COMMIT' in os.environ:
                commit_hash = os.environ['HEROKU_SLUG_COMMIT']
                repo_url = f'https://github.com/jareddantis/rico-bot/tree/{commit_hash}'
                version = commit_hash[:7]
            else:
                repo_url = 'https://github.com/jareddantis/rico-bot'
                version = 'Unknown version'

        # Build and send embed
        embed = RicoEmbed(
            header=f'version {version}',
            header_url=repo_url,
            title=f'About {ctx.guild.me.display_name}',
            thumbnail_url=self.bot.user.avatar.url,
            color=Color.green(),
            description='\n\n'.join(['\n'.join(i) for i in info])
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
