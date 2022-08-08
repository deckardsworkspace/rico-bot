from clients.spotify_client import Spotify
from dataclass.custom_embed import create_error_embed
from nextcord import Interaction
from nextcord.ext import ipc
from nextcord.ext.commands import Bot
from yaml import safe_load
from .api import APIClient


class RicoBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Load config
        with open('config.yml') as f:
            try:
                self.config = safe_load(f)
            except Exception as e:
                raise ValueError(f'Error parsing config.yml: {e}')
        
        # Create API client
        self._api = APIClient(self.config)

        # Create Spotify client
        try:
            spotify_client_id = self.config['bot']['spotify']['client_id']
            spotify_client_secret = self.config['bot']['spotify']['client_secret']
        except KeyError:
            raise ValueError('Missing Spotify client ID or secret')
        else:
            self._spotify = Spotify(spotify_client_id, spotify_client_secret)

        # Start IPC server
        self.ipc = ipc.server.Server(
            self,
            port=self.config['ipc']['port'],
            secret_key=self.config['ipc']['secret']
        )

    async def on_ready(self):
        print('Logged in as {0}!'.format(self.user))
        
        # Add cogs
        self.load_extension('cogs')

    async def on_ipc_ready(self):
        print('IPC ready!')

    async def on_application_command_error(self, itx: Interaction, error: Exception):
        error_embed = create_error_embed(
            title='Error processing command',
            body=str(error)
        )
        try:
            if itx.response.is_done():
                await itx.followup.send(embed=error_embed)
            else:
                await itx.response.send_message(embed=error_embed)
        except:
            await itx.channel.send(embed=error_embed)

    async def on_ipc_error(self, endpoint: str, error: Exception):
        print(f'IPC error: {endpoint}: {error}')
    
    @property
    def api(self) -> APIClient:
        return self._api
    
    @property
    def spotify(self) -> Spotify:
        return self._spotify
