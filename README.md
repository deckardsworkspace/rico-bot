# rico-bot

Rico is a Discord bot that allows you to recommend stuff to others, manage stuff recommended to you, keep conversations going in threads, and even play music.

This bot is best deployed on a cloud platform service like Heroku, but can be hosted at home or on a VPS. Configuration is performed through environment variables.

Data is stored in a Firebase Realtime Database (handled by [pyrebase](https://github.com/thisbejim/Pyrebase)), and music data is pulled from Spotify (handled by [spotipy](https://github.com/plamere/spotipy)) and YouTube (handled by [youtubesearchpython](https://github.com/alexmercerind/youtube-search-python)).

Since the Discord.py library was discontinued, Rico now uses the community fork [Nextcord](https://github.com/nextcord/nextcord) to interface with the Discord API.

**Table of Contents**

- [rico-bot](#rico-bot)
  - [Features](#features)
  - [Requirements](#requirements)
    - [Use a publicly available Lavalink server](#use-a-publicly-available-lavalink-server)
    - [Host Lavalink on a VPS](#host-lavalink-on-a-vps)
    - [Host Lavalink at home](#host-lavalink-at-home)
  - [Configuration & deployment](#configuration--deployment)
    - [Thread manager configuration (optional)](#thread-manager-configuration-optional)
    - [Music player configuration (optional)](#music-player-configuration-optional)
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

- **Music playback**

  Rico has rudimentary support for YouTube, Spotify, and Twitch playback in voice channels, powered by [Lavalink](https://github.com/freyacodes/Lavalink) and [Lavalink.py.](https://github.com/Devoxin/Lavalink.py) See **[Requirements](Requirements)** below.

  Rico also has a command `info` for displaying stats about the bot's host and Lavalink nodes.

  *This is an optional feature.* See **[Configuration & deployment](#music-player-configuration-optional)** to learn how to enable this feature.

## Requirements

* Python 3.9+
* `pip install -r requirements.txt` to install packages if testing locally (remember to use a virtualenv)
* A Discord bot account (get one [here](https://discord.com/developers/applications))
* A Spotify developer account (get one [here](https://developer.spotify.com/dashboard/))
* A working Firebase Realtime Database (create one [here](https://console.firebase.google.com/))

Some of the requirements installed by `pip` require that the Python development headers, like `Python.h`, be present in your system. Others require that a GCC compiler be present as well. Instructions differ per operating system, but generally for Debian/Ubuntu systems you can do `sudo apt install python3-dev build-essential`.

If you want to use Rico's music playing functionality, you will also need a working and reachable Lavalink server. Downloads and sample configuration for Lavalink is available at its [official repository.](https://github.com/freyacodes/Lavalink)

You can get a working Lavalink instance in three ways:

### Use a publicly available Lavalink server

Some hosting providers, such as [Something.Host,](https://support.something.host/en/article/lavalink-hosting-okm26z/) offer a publicly available Lavalink server.

Grab the Lavalink hostname, port, and password on their site, then head over to **[Configuration & deployment.](#configuration--deployment)**

### Host Lavalink on a VPS

Most people will go about creating a Lavalink server by setting up a Linux virtual private server (VPS), from providers such as DigitalOcean and Azure, and running Lavalink there.

After setting up your VPS,

- install Java (version 13 is recommended),
- download Lavalink and the sample configuration `application.yml`,
- edit `application.yml` to your liking (make sure you change the password!)
- run Lavalink with `java -jar Lavalink.jar`

If you are hosting Rico on the same VPS, your Lavalink server will be accessible at `127.0.0.1`. Otherwise make sure to grab the public IP of your VPS and the port set in your `application.yml`, then head over to **[Configuration & deployment.](#configuration--deployment)**

### Host Lavalink at home

A VPS costs money. This isn't an option for everyone, so the next best thing would be to set this up yourself and run a Lavalink server at home for free. Be warned, however, that this will require a dependable Internet connection and a computer that runs 24/7 if you want your bot to be able to play music 24/7.

The process is largely similar to hosting Lavalink on a VPS. However, if you do not plan to host Rico on the same machine, you will have to make sure that your machine is accessible remotely via its public IP address and that the Lavalink port you set is open to the Internet.

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

### Music player configuration (optional)

If you want to make use of the music player, you will also need to set these variables:

|Config key|Description|
|-----|-----|
|`ENABLE_MUSIC`|Set to `1` if you want to enable Rico's music player functionality.|
|`LAVALINK`|Serialized list of your Lavalink nodes in JSON format.|
|`INACTIVE_SEC`|Time to wait (in seconds) before disconnecting for inactivity. Must be > 0.|

To create a valid `LAVALINK` configuration, edit the following code accordingly and run it with Python:

```python
import json

nodes = [
    {
        # Unique ID for your Lavalink server.
        # This will be used to identify servers in logs.
        'id': 'default-node',

        # Lavalink server region.
        # This will be used by Lavalink to identify which server
        # to use depending on what server is the closest to the users.
        # See https://nextcord.readthedocs.io/en/latest/api.html#nextcord.VoiceRegion
        'region': 'us',

        # Lavalink server URL.
        # This must match the format `hostname:port`.
        # for example: `lava.link:80` (do not add 'http://' or 'https://'!)
        'server': 'example.com:2333',

        # Lavalink server password.
        # Must match the password in Lavalink's `application.yml` file.
        'password': 'password'
    }#, {...}   You can specify more than one node for redundancy.
]

print(json.dumps(json.dumps(nodes)))
```

The script will print out a serialized JSON string, which you should then set `LAVALINK` to.

Make sure your Lavalink server(s) are reachable with these parameters. The bot will throw an error and fail to play music if it cannot authenticate with your server.

## Usage

If you're testing locally, run `python bot.py`. Note that depending on your environment, your config must either be set as environment variables or enumerated in an `.env` file as `KEY="VALUE"` pairs.

Once the bot is up and running in your server, type `<COMMAND_PREFIX>help` for a list of commands.

### Owner-only commands

You, as the owner of your Rico instance, have access to the owner-only command `<COMMAND_PREFIX>reload`, which force-reloads every cog and its commands. Use this to quickly test features that you implement in Rico without having to restart the entire bot.

## Documentation and support

Rico is a personal project, made to cater to me and a few friends. As such, should you choose to deploy this bot for personal use, please do not expect support from me if anything goes wrong.

Many of the important functions in Rico's code are documented, and other undocumented parts of the code will be documented once Rico reaches satisfactory levels of stability.

You can add new commands as a class in `cogs/` that inherits from `nextcord.ext.commands.Cog`.
