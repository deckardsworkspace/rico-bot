from nextcord.ext import ipc
from nextcord.ext.commands import Cog
from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from util.api import APIClient
    from util.rico_bot import RicoBot


class IPCCog(Cog):
    """
    Cog for handling IPC routes
    """
    def __init__(self, bot: 'RicoBot'):
        self._bot = bot
        print(f'Loaded cog: {self.__class__.__name__}')

    @ipc.server.route()
    async def get_mutual_guilds(self, data: Any):
        # Get all thread-managed guilds
        managed_guilds = self._bot.api.get_thread_managed_guilds()

        # Get all mutual guilds
        guilds = []
        for guild in self._bot.guilds:
            if guild.get_member(data.user_id) is not None:
                guilds.append({
                    'id': guild.id,
                    'name': guild.name,
                    'icon': guild.icon.url,
                    'manage_threads': guild.id in managed_guilds
                })

        print(guilds)
        return guilds
