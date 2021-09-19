import nextcord
import json
import lavalink
from collections import deque
from lavalink.events import *
from nextcord.ext import commands
from util import *


class Music(commands.Cog):
    """
    https://github.com/Devoxin/Lavalink.py/blob/master/examples/music.py

    This example cog demonstrates basic usage of Lavalink.py, using the DefaultPlayer.
    As this example primarily showcases usage in conjunction with discord.py, you will need to make
    modifications as necessary for use with another Discord library.
    Usage of this cog requires Python 3.6 or higher due to the use of f-strings.
    Compatibility with Python 3.5 should be possible if f-strings are removed.
    """
    def __init__(self, bot: commands.Bot, db, spotify: Spotify):
        self.bot = bot
        self.db = db
        self.spotify = spotify

        if not hasattr(bot, 'lavalink'):  # This ensures the client isn't overwritten during cog reloads.
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node(
                get_var('LAVALINK_SERVER'),
                get_var('LAVALINK_PORT'),
                get_var('LAVALINK_PASSWORD'),
                'ph', 'default-node'
            )

        lavalink.add_event_hook(self.track_hook)

    def cog_unload(self):
        """ Cog unload handler. This removes any event hooks that were registered. """
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        """ Command before-invoke handler. """
        guild_check = ctx.guild is not None
        #  This is essentially the same as `@commands.guild_only()`
        #  except it saves us repeating ourselves (and also a few lines).

        if guild_check:
            await self.ensure_voice(ctx)
            #  Ensure that the bot and command author share a mutual voicechannel.

        return guild_check

    async def ensure_voice(self, ctx):
        """ This check ensures that the bot and command author are in the same voicechannel. """
        player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
        # Create returns a player if one exists, otherwise creates.
        # This line is important because it ensures that a player always exists for a guild.

        # Most people might consider this a waste of resources for guilds that aren't playing, but this is
        # the easiest and simplest way of ensuring players are created.

        # These are commands that require the bot to join a voicechannel (i.e. initiating playback).
        # Commands such as volume/skip etc don't require the bot to be in a voicechannel so don't need listing here.
        should_connect = ctx.command.name in ('play', 'p')

        if not ctx.author.voice or not ctx.author.voice.channel:
            # Our cog_command_error handler catches this and sends it to the voicechannel.
            # Exceptions allow us to "short-circuit" command invocation via checks so the
            # execution state of the command goes no further.
            raise commands.CommandInvokeError('Join a voicechannel first.')

        if not player.is_connected:
            if not should_connect:
                raise commands.CommandInvokeError('Not connected.')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise commands.CommandInvokeError('I need the `CONNECT` and `SPEAK` permissions.')

            player.store('channel', ctx.channel.id)
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        else:
            if int(player.channel_id) != ctx.author.voice.channel.id:
                raise commands.CommandInvokeError('You need to be in my voicechannel.')

    async def track_hook(self, event):
        # Recover context from DB
        guild_id = None
        ctx = None
        if hasattr(event, 'player'):
            guild_id = event.player.guild_id
            channel_id = self.db.child('player').child(guild_id).child('channel').get().val()
            message_id = self.db.child('player').child(guild_id).child('message').get().val()
            if channel_id and message_id:
                channel = self.bot.get_channel(channel_id)
                message = await channel.fetch_message(message_id)
                ctx = await self.bot.get_context(message)

        if isinstance(event, QueueEndEvent):
            # There are no tracks left in the player's queue.
            # To save on resources, we can tell the bot to disconnect from the voice channel.
            guild = self.bot.get_guild(int(guild_id))
            await guild.voice_client.disconnect(force=True)

            # Delete queue from DB
            self.db.child('player').child(guild_id).remove()

            # Send queue finished embed
            embed = nextcord.Embed(color=nextcord.Color.blurple())
            embed.title = 'Queue finished'
            embed.description = 'Stopped the player and disconnected from the channel'
            await ctx.send(embed=embed)
        elif isinstance(event, TrackStartEvent):
            # Send now playing embed
            embed = nextcord.Embed(color=nextcord.Color.yellow())
            embed.title = 'Now playing'
            embed.description = event.track.title
            await ctx.send(embed=embed)

            # Check if the queue for this guild is empty
            queue_items = self.db.child('player').child(guild_id).child('queue').get().val()
            queue = deque(json.loads(queue_items))
            if len(queue):
                # Queue up the next (valid) track
                while len(queue):
                    next_track = queue.popleft()
                    query = f'ytsearch:{next_track[0]} {next_track[1]}'
                    if await self.enqueue(query, event.player, ctx=ctx, quiet=True):
                        # Store the new queue back into DB
                        self.db.child('player').child(guild_id).child('queue').set(json.dumps(queue, cls=DequeEncoder))
                        break

    async def enqueue(self, query: str, player, ctx: commands.Context, quiet: bool = False) -> bool:
        # Get the results for the query from Lavalink.
        results = await player.node.get_tracks(query)

        # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
        # Alternatively, results['tracks'] could be an empty array if the query yielded no tracks.
        if not results or not results['tracks']:
            if not quiet:
                await ctx.send(f'Nothing found for `{query}`!')
            return False

        embed = nextcord.Embed(color=nextcord.Color.blurple())

        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL
        #   PLAYLIST_LOADED - direct URL to playlist
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
        if results['loadType'] == 'PLAYLIST_LOADED':
            tracks = results['tracks']

            for track in tracks:
                # Add all of the tracks from the playlist to the queue.
                player.add(requester=ctx.author.id, track=track)

            embed.title = 'Playlist enqueued'
            embed.description = f'{results["playlistInfo"]["name"]} - {len(tracks)} tracks'
        else:
            track = results['tracks'][0]
            embed.title = 'Track enqueued'
            embed.description = f'[{track["info"]["title"]}]({track["info"]["uri"]})'

            # You can attach additional information to audiotracks through kwargs, however this involves
            # constructing the AudioTrack class yourself.
            track = lavalink.models.AudioTrack(track, ctx.author.id, recommended=True)
            player.add(requester=ctx.author.id, track=track)

        if not quiet:
            await ctx.send(embed=embed)

            # We don't want to call .play() if the player is playing as that will effectively skip
            # the current track.
            if not player.is_playing:
                await player.play()
        
        return True

    @commands.command(aliases=['p'])
    async def play(self, ctx: commands.Context, *, query: str):
        """ Searches and plays a song from a given query. """
        # Save the context for later
        self.db.child('player').child(str(ctx.guild.id)).child('channel').set(ctx.channel.id)
        self.db.child('player').child(str(ctx.guild.id)).child('message').set(ctx.message.id)

        # Get the player for this guild from cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip('<>')

        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        if not check_url(query):
            return await self.enqueue(f'ytsearch:{query}', player, ctx=ctx)
        else:
            # Query is a URL
            if check_spotify_url(query):
                # Query is a Spotify URL.
                try:
                    sp_type, sp_id = parse_spotify_url(query, valid_types=['track', 'album', 'playlist'])
                except SpotifyInvalidURLError:
                    return await ctx.reply('Only Spotify track, album, and playlist URLs are supported.')

                if sp_type == 'track':
                    # Get track details from Spotify
                    track_name, track_artist = self.spotify.get_track(sp_id)
                    return await self.enqueue(f'ytsearch:{track_name} {track_artist}', player, ctx=ctx)
                else:
                    # Get playlist or album tracks from Spotify
                    list_name, list_author, tracks = self.spotify.get_tracks(sp_type, sp_id)
                    track_queue = deque(tracks)

                    if len(tracks) < 1:
                        # Empty list
                        return await ctx.reply(f'Spotify {sp_type} is empty.')
                    elif len(tracks) == 1:
                        # Single track
                        return await self.enqueue(f'ytsearch:{tracks[0][0]} {tracks[0][1]}', player, ctx=ctx)
                    else:
                        # Multiple tracks
                        # There is no way to queue multiple items in one batch through Lavalink.py,
                        # hence we play the first one and store the rest of the queue in DB for later.

                        # Play the first valid track
                        while len(track_queue):
                            track = track_queue.popleft()
                            result = await self.enqueue(f'ytsearch:{track[0]} {track[1]}', player, ctx=ctx, quiet=True)
                            if result:
                                break
                            await ctx.send(f'Error enqueueing "{track[0]}".')

                        # Save the rest to DB then play
                        if len(track_queue):
                            encoded_queue = json.dumps(track_queue, cls=DequeEncoder)
                            self.db.child('player').child(str(ctx.guild.id)).child('queue').set(encoded_queue)
                        if not player.is_playing:
                            await player.play()

                        # Send enqueued embed
                        color = nextcord.Color.blurple()
                        embed = nextcord.Embed(color=color)
                        embed.title = f'Spotify {sp_type} enqueued'
                        embed.description = f'[{list_name}]({query}) by {list_author} ({len(tracks)} tracks)'
                        return await ctx.reply(embed=embed)
            elif check_twitch_url(query):
                return await self.enqueue(query, player, ctx=ctx)
            else:
                return await self.enqueue(f'ytsearch:{query}', player, ctx=ctx)

    @commands.command()
    async def pause(self, ctx):
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Pause the player.
        if not player.paused:
            await player.set_pause(pause=True)
        else:
            await ctx.reply('Already paused.')
    
    @commands.command()
    async def unpause(self, ctx):
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Unpause the player.
        if player.paused:
            await player.set_pause(pause=False)
            await ctx.reply('Unpaused the player.')
        else:
            await ctx.reply('Already unpaused.')
    
    @commands.command()
    async def skip(self, ctx):
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        
        # Skip track.
        await player.skip()
        await ctx.reply('Skipped the track.')

    @commands.command(aliases=['stop', 'dc'])
    async def disconnect(self, ctx):
        """ Disconnects the player from the voice channel and clears its queue. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.is_connected:
            # We can't disconnect, if we're not connected.
            return await ctx.reply('Not connected.')

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not disconnect the bot.
            return await ctx.reply('You\'re not in my voicechannel!')

        # Clear the queue to ensure old tracks don't start playing
        # when someone else queues something.
        player.queue.clear()
        self.db.child('player').child(str(ctx.guild.id)).remove()

        # Stop the current track so Lavalink consumes less resources.
        await player.stop()

        # Disconnect from the voice channel.
        await ctx.voice_client.disconnect(force=True)
        await ctx.send('*⃣ | Stopped the player and disconnected from the channel.')
