# rico-bot

Rico is a Discord bot that allows you to recommend stuff to others, manage stuff recommended to you, and keep conversations going in threads.

This bot is best deployed on a cloud platform service like Heroku, but can be hosted at home or on a VPS. Configuration is performed through environment variables.

Data is stored in a Firebase Realtime Database (handled by [pyrebase](https://github.com/thisbejim/Pyrebase)), and music data is pulled from Spotify (handled by [spotipy](https://github.com/plamere/spotipy)).

**Table of Contents**

- [rico-bot](#rico-bot)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Configuration & deployment](#configuration--deployment)
    - [Thread manager configuration (optional)](#thread-manager-configuration-optional)
  - [Usage](#usage)
    - [Owner-only commands](#owner-only-commands)
  - [Documentation and support](#documentation-and-support)

## Features

- **Recommendation lists**
  
  Every server member has their own list of recommendations, like a personal corkboard of links, songs, albums, and notes. The server itself has its own list, to which any member can add stuff that they think the rest of the server will like.

  When someone recommends a YouTube video, Spotify track, artist, or album to someone else, Rico will automatically fetch information about these items so you can easily see what's been recommended.

  Anyone can add to and view anyone's list, but only list owners can remove from their own list. Similarly, anyone can view the server's list, but only server administrators can remove from the server's list.

- **Thread management**

  Threads are extremely useful for managing lengthy discussions on topics that would have otherwise belonged in a separate full-blown text channel. Rico allows you to keep these threads alive for much longer, automatically unarchiving these threads indefinitely until you tell him to stop.

  *This is an optional feature.* See **[Configuration & deployment](#thread-manager-configuration-optional)** to learn how to enable this feature.

## Requirements

* Python 3.9+
* `pip install -r requirements.txt` to install packages if testing locally (remember to use a virtualenv)
* A Discord bot account (get one [here](https://discord.com/developers/applications))
* A Spotify developer account (get one [here](https://developer.spotify.com/dashboard/))
* A working Firebase Realtime Database (create one [here](https://console.firebase.google.com/))

Some of the requirements installed by `pip` require that the Python development headers, like `Python.h`, be present in your system. Others require that a GCC compiler be present as well. Instructions differ per operating system, but generally for Debian/Ubuntu systems you can do `sudo apt install python3-dev build-essential`.

## Configuration & deployment

Populate your chosen platform's build/environment/config variables with your own configuration, according to the template below. **All of the following keys are required.**

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

### Thread manager configuration (optional)

Rico has the ability to persist Discord server threads indefinitely. To enable this functionality, set the following variable:

|Config key|Description|
|-----|-----|
|`ENABLE_THREADMGR`|Set to `1` if you want to enable Rico's automatic thread unarchiver.|

Even with `ENABLE_THREADMGR` set to `1`, Rico will not monitor servers for archived threads until you explicitly tell him to using the `<COMMAND_PREFIX>ttm` command.

Once Rico's thread manager is enabled on your server, threads that get automatically archived by Discord or manually archived by a moderator will be instantly unarchived. To exclude a server from being unarchived, e.g. when discussion on a thread is finished, use the `<COMMAND_PREFIX>tte` command **from within that thread.**

## Usage

If you're testing locally, run `python bot.py`. Note that depending on your environment, your config must either be set as environment variables or enumerated in an `.env` file as `KEY="VALUE"` pairs.

Once the bot is up and running in your server, type `<COMMAND_PREFIX>help` for a list of commands.

### Owner-only commands

You, as the owner of your Rico instance, have access to the owner-only command `<COMMAND_PREFIX>reload`, which force-reloads every cog and its commands. Use this to quickly test features that you implement in Rico without having to restart the entire bot.

## Documentation and support

Rico is a personal project, made to cater to me and a few friends. As such, should you choose to deploy this bot for personal use, please do not expect support from me if anything goes wrong.

Many of the important functions in Rico's code are documented, and other undocumented parts of the code will be documented once Rico reaches satisfactory levels of stability.

You can add new commands as a class in `cogs/` that inherits from `nextcord.ext.commands.Cog`.
