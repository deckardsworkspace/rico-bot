from nextcord import Activity, ActivityType, Intents
from nextcord.ext.tasks import loop
from util.rico_bot import RicoBot


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
    client.ipc.start()
    client.run(client.config['bot']['discord_token'])
