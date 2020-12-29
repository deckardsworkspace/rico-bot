from discord import Activity, ActivityType
from discord.ext.commands import Bot
from discord.ext.tasks import loop
from config import get_var, get_pyrebase_config
from util import Spotify
import pyrebase
import commands

firebase = pyrebase.initialize_app(get_pyrebase_config())
auth = firebase.auth()
db = firebase.database()
spotify = Spotify()
client = Bot(command_prefix='rc!')


@client.event
async def on_ready():
    print('Logged on as {0}!'.format(client.user))


@client.event
async def on_message(message):
    # Ignore messages sent by this bot
    if message.author == client.user:
        return

    await client.process_commands(message)


@loop(seconds=120)
async def update_presence():
    activity = Activity(name='you | rc!help', type=ActivityType.listening)
    await client.change_presence(activity=activity)


@update_presence.before_loop
async def update_presence_before():
    await client.wait_until_ready()


update_presence.start()
client.add_cog(commands.Recommendation(client, db, spotify))
client.run(get_var('DISCORD_TOKEN'))
