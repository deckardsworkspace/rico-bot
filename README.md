# rico-bot

Rico is a Discord bot that allows you to recommend stuff to others and have stuff recommended to you.

Rico also has rudimentary support for YouTube, Spotify, and Twitch playback in voice channels, powered by [Lavalink](https://github.com/freyacodes/Lavalink) and [Lavalink.py.](https://github.com/Devoxin/Lavalink.py) See [#requirements](https://github.com/jareddantis/rico-bot#requirements) below.

This bot is designed to be deployed on a cloud platform service like Heroku. Configuration is performed through build/environment variables.

Data is stored in a Firebase Realtime Database (handled by [pyrebase](https://github.com/thisbejim/Pyrebase)), and music data is pulled from Spotify (handled by [spotipy](https://github.com/plamere/spotipy)).

Since the Discord.py library was discontinued, Rico now uses the community fork [Nextcord](https://github.com/nextcord/nextcord) to interface with the Discord API.

## Requirements

* Python 3.9+
* `pip install -r requirements.txt` to install packages if testing locally (remember to use a virtualenv)
* A Discord bot account (get one [here](https://discord.com/developers/applications))
* A Spotify developer account (get one [here](https://developer.spotify.com/dashboard/))
* A working Firebase Realtime Database (create one [here](https://console.firebase.google.com/))

If you want to use Rico's music playing functionality, which is **enabled by default**, you will also need a working and reachable Lavalink server. Downloads and sample configuration for Lavalink is available at its [official repository.](https://github.com/freyacodes/Lavalink)

Most people will go about creating a Lavalink server by setting up a Linux virtual private server (VPS), from providers such as DigitalOcean and Azure, and running Lavalink there.

A VPS costs money, however. This isn't an option for everyone, so the next best thing would be to set this up yourself and run a Lavalink server at home for free. Be warned, however, that this will require a dependable Internet connection and a computer that runs 24/7.

If you are setting up this bot by yourself, chances are you also have enough knowledge to set up a VPS or a home server for Lavalink, therefore I will not cover that here. There are tutorials on the Internet that can explain this far better than I can :)

## Configuration & deployment

Populate your chosen platform's build/environment/config variables with your own configuration, according to the template below.

|Config key|Description|
|-----|-----|
|`BOT_PREFIX`|Command prefix for the bot|
|`DISCORD_TOKEN`|Discord bot token|
|`FIREBASE_KEY`|Firebase Realtime Database API key|
|`FIREBASE_AUTHDOMAIN`|Firebase Realtime Database auth domain|
|`FIREBASE_DBURL`|Firebase Realtime Database URL|
|`FIREBASE_BUCKET`|Firebase Realtime Database bucket|
|`FIREBASE_CLIENT_EMAIL`|Firebase service account client email|
|`FIREBASE_CLIENT_ID`|Firebase service account client ID|
|`FIREBASE_PRIVATE_KEY`|Firebase service account private key|
|`FIREBASE_PRIVATE_KEY_ID`|Firebase service account private key ID|
|`SPOTIFY_ID`|Spotify client ID|
|`SPOTIFY_SECRET`|Spotify client secret|

If you also want to make use of the music player, you will also need to set these variables:

|Config key|Description|
|-----|-----|
|`LAVALINK_SERVER`|IP address of your Lavalink server|
|`LAVALINK_PORT`|Port of your Lavalink server|
|`LAVALINK_PASSWORD`|Password for your Lavalink server|

Make sure your Lavalink server is reachable with these parameters. The bot will throw an error if it cannot authenticate with your server.

If you **don't** want to make use of the music player, simply remove the following line from `cogs/__init__.py` to disable this functionality:

```
# Add cogs
...
bot.add_cog(Music(bot, db, spotify))
...
```

If you're testing locally, use `python app.py`. Note that if you're testing locally, your config must be set as environment variables.

Once the bot is up and running, type `<COMMAND_PREFIX>help` for a list of commands.

## Documentation and support

Rico is a personal project, made to cater a server for me and a few friends. As such, should you choose to deploy this bot for personal use, please do not expect support from me if anything goes wrong.

Many of the important functions in Rico's code are documented, and other undocumented parts of the code will be documented once Rico reaches satisfactory levels of stability.

You can add new commands as a class in `cogs/` that inherits from `nextcord.ext.commands.Cog`.
