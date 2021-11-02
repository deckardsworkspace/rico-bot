from nextcord import Activity, ActivityType, Embed, Color, Message
from nextcord.ext.commands import Bot, CommandNotFound, Context, errors
from nextcord.ext.tasks import loop
from util import get_var, VoiceCommandError


# Create Discord client
bot_prefix = get_var('BOT_PREFIX')
client = Bot(command_prefix=bot_prefix)
client.remove_command('help')


@client.event
async def on_ready():
    print('Logged on as {0}!'.format(client.user))
    
    # Add cogs
    client.load_extension('cogs')

@client.event
async def on_message(message: Message):
    # Ignore messages sent by this bot
    if message.author == client.user:
        return
    
    try:
        await client.process_commands(message)
    except VoiceCommandError as e:
        embed = Embed(color=Color.red(), title=f'Error while processing command', description=e.message)
        await message.reply(embed=embed)


@client.event
async def on_command_error(ctx: Context, error):
    embed = Embed(color=Color.red(), title=f'Error while processing command `{ctx.invoked_with}`')

    if type(error) in [errors.PrivateMessageOnly, errors.NoPrivateMessage]:
        embed.description = str(error)
    elif type(error) is CommandNotFound:
        embed.description = 'Invalid command.'
    else:
        embed.description = f'`{type(error).__name__}`: {error}'

    await ctx.reply(embed=embed)


@loop(seconds=120)
async def bot_loop():
    # Change presence
    status = "{0} {1} | {2}help".format(len(client.guilds), "servers", bot_prefix)
    activity = Activity(name=status, type=ActivityType.listening)
    await client.change_presence(activity=activity)


@bot_loop.before_loop
async def bot_loop_before():
    await client.wait_until_ready()


if __name__ == '__main__':
    bot_loop.start()
    client.run(get_var('DISCORD_TOKEN'))
