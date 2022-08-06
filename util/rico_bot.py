from dataclass.custom_embed import create_error_embed
from nextcord import Interaction
from nextcord.ext import ipc
from nextcord.ext.commands import Bot
from yaml import safe_load


class RicoBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Load config
        with open('config.yml') as f:
            try:
                self.config = safe_load(f)
            except Exception as e:
                raise ValueError(f'Error parsing config.yml: {e}')

        # Start IPC server
        self.ipc = ipc.server.Server(
            self,
            port=self.config['ipc']['server_port'],
            secret_key=self.config['ipc']['secret_key']
        )

    async def on_ready(self):
        print('Logged in as {0}!'.format(self.user))
        
        # Add cogs
        self.load_extension('cogs')

    async def on_ipc_ready(self):
        print('IPC ready!')

    async def on_application_command_error(self, itx: Interaction, error: Exception):
        await itx.channel.send(embed=create_error_embed(
            title='Error processing command',
            body=error
        ))

    async def on_ipc_error(self, endpoint: str, error: Exception):
        print(f'IPC error: {endpoint}: {error}')