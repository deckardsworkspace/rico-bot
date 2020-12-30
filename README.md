# rico-bot

This is a Discord bot that allows you to recommend music to others and have music recommended to you, kind of like having pinned messages but for music.

This bot is designed to be deployed on a cloud platform service like Heroku. Configuration is performed through build/environment variables.

Data is stored in a Firebase Realtime Database (handled by [pyrebase](https://github.com/thisbejim/Pyrebase)), and music data is pulled from Spotify (handled by [spotipy](https://github.com/plamere/spotipy)).

## Requirements

* Python 3.9+
* `pip install -r requirements.txt` to install packages if testing locally (remember to use a virtualenv)

## Configuration & deployment
1. Refer to the [Discord.py Docs](https://discordpy.readthedocs.io/en/latest/discord.html#discord-intro) to create a Bot account and add it to a guild/server
2. Populate your chosen platform's build vars with your own configuration

|Config key|Description|
|-----|-----|
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

3. Deploy to your chosen service, or if you're testing locally, `python app.py`. Note that if you're testing locally, your config must be set as environment variables.
4. Type `rc!help` for a list of commands.

## Documentation
Refer to Docstrings and Comments for function documentation. You can add new commands as a class in `commands/` that inherits from `discord.ext.commands.Cog`.
