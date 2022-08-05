from dataclass.custom_embed import create_error_embed
from nextcord import Activity, ActivityType, Intents, Interaction
from nextcord.ext import ipc
from nextcord.ext.commands import Bot
from nextcord.ext.tasks import loop
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


# Create Discord client
intents = Intents.default()
intents.members = True
client = RicoBot(intents=intents)


@loop(seconds=3600)
async def bot_loop():
    # Change presence
    status = f'{len(client.guilds)} servers | /help'
    activity = Activity(name=status, type=ActivityType.listening)
    await client.change_presence(activity=activity)


@bot_loop.before_loop
async def bot_loop_before():
    await client.wait_until_ready()


if __name__ == '__main__':
    bot_loop.start()
    client.run(client.config['bot']['discord_token'])
