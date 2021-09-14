import pyrebase
import commands
from nextcord import Activity, ActivityType
from nextcord.ext.commands import Bot, errors, CommandNotFound
from nextcord.ext.tasks import loop
from config import get_var, get_pyrebase_config
from util import Spotify

firebase = pyrebase.initialize_app(get_pyrebase_config())
auth = firebase.auth()
db = firebase.database()
spotify = Spotify()
client = Bot(command_prefix='rc!')
status_guilds = False


@client.event
async def on_ready():
    print('Logged on as {0}!'.format(client.user))


@client.event
async def on_message(message):
    # Ignore messages sent by this bot
    if message.author == client.user:
        return
    await client.process_commands(message)


@client.event
async def on_command_error(ctx, error):
    if type(error) in [errors.PrivateMessageOnly, errors.NoPrivateMessage]:
        await ctx.reply(str(error))
        await ctx.message.delete(delay=5.0)
    elif type(error) is CommandNotFound and ctx.invoked_with == "h":
        await ctx.reply('Command not found, did you mean `rc!help`?')
    else:
        await ctx.reply('\n'.join([
            'Error encountered while executing command {}.'.format(ctx.author.mention, ctx.invoked_with),
            '`{}`: `{}`'.format(type(error).__name__, str(error)),
            '\nPlease report bugs to the official support server at https://discord.gg/njtK9G6QRG'
        ]))


@loop(seconds=120)
async def update_presence():
    global status_guilds

    status_template = "{0} {1} | rc!help"
    if status_guilds:
        status = status_template.format(len(client.guilds), "servers")
    else:
        num_users = 0
        for guild in client.guilds:
            num_users += guild.member_count - 1
        status = status_template.format(num_users, "users")

    activity = Activity(name=status, type=ActivityType.listening)
    await client.change_presence(activity=activity)
    status_guilds = not status_guilds


@update_presence.before_loop
async def update_presence_before():
    await client.wait_until_ready()


update_presence.start()
client.add_cog(commands.Recommendation(client, db, spotify, get_var('FIREBASE_KEY')))
client.add_cog(commands.Export(client, db, spotify))
client.run(get_var('DISCORD_TOKEN'))
