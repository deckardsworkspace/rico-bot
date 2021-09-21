from nextcord import Activity, ActivityType, Embed, Color
from nextcord.ext.commands import Bot, errors, CommandNotFound
from nextcord.ext.tasks import loop
from util import get_var, VoiceCommandError


# Create Discord client
client = Bot(command_prefix=get_var('BOT_PREFIX'))
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
    
    try:
        await client.process_commands(message)
    except VoiceCommandError as e:
        embed = Embed(color=Color.red(), title=f'**{e.message}**')
        await message.reply(embed=embed)


@client.event
async def on_command_error(ctx, error):
    if type(error) in [errors.PrivateMessageOnly, errors.NoPrivateMessage]:
        await ctx.reply(str(error))
        await ctx.message.delete(delay=5.0)
    elif type(error) is CommandNotFound:
        await ctx.reply('Invalid command.')
    else:
        print(error)
        await ctx.reply(f'`{type(error).__name__}` encountered while executing `{ctx.invoked_with}`.\n{error.message}')


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
