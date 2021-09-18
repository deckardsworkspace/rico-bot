from nextcord import Activity, ActivityType
from nextcord.ext.commands import Bot, errors, CommandNotFound
from nextcord.ext.tasks import loop
from util import get_var


# Create Discord client
client = Bot(command_prefix='rc!')
client.remove_command('help')


@client.event
async def on_ready():
    print('Logged on as {0}!'.format(client.user))
    client.load_extension('cogs')


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
    elif type(error) is CommandNotFound:
        await ctx.reply('Invalid command.')
    else:
        await ctx.reply('\n'.join([
            'Error encountered while executing command {}.'.format(ctx.author.mention, ctx.invoked_with),
            '`{}`: `{}`'.format(type(error).__name__, str(error)),
            '\nPlease report bugs to the official support server at https://discord.gg/njtK9G6QRG'
        ]))


@loop(seconds=120)
async def bot_loop():
    # Change presence
    status = "{0} {1} | rc!help".format(len(client.guilds), "servers")
    activity = Activity(name=status, type=ActivityType.listening)
    await client.change_presence(activity=activity)


@bot_loop.before_loop
async def bot_loop_before():
    await client.wait_until_ready()


bot_loop.start()
client.run(get_var('DISCORD_TOKEN'))
