import nextcord
import json
import lavalink
from collections import deque
from lavalink.events import *
from lavalink.models import DefaultPlayer
from nextcord.ext import commands
from util import *
from random import shuffle
from typing import Deque


class Music(commands.Cog):
    """ Based on https://github.com/Devoxin/Lavalink.py/blob/master/examples/music.py """
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

    def __enqueue(self, guild_id: str, query: str):
        try:
            queue = self.__get_queue(guild_id)
        except QueueEmptyError:
            queue = deque()
        queue.append(query)
        self.__set_queue(guild_id, queue)

    def __enqueue_multiple(self, guild_id: str, queries: list[str]):
        try:
            queue = self.__get_queue(guild_id)
        except QueueEmptyError:
            queue = deque()
        queue.extend(queries)
        self.__set_queue(guild_id, queue)

    def __dequeue(self, guild_id: str) -> str:
        queue = self.__get_queue(guild_id)
        query = queue.popleft()
        self.__set_queue(guild_id, queue)
        return query

    def __get_queue(self, guild_id: str) -> Deque[str]:
        queue_items = self.db.child('player').child(guild_id).child('queue').get().val()
        if queue_items:
            return deque(json.loads(queue_items))
        raise QueueEmptyError

    def __set_queue(self, guild_id: str, queue: Deque[str]):
        self.db.child('player').child(guild_id).child('queue').set(json.dumps(queue, cls=DequeEncoder))

    def cog_unload(self):
        """ Cog unload handler. This removes any event hooks that were registered. """
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        """ Command before-invoke handler. """
        # Only allow music commands in guilds
        guild_check = ctx.guild is not None
        if guild_check:
            # Ensure that the bot and command author share a mutual voice channel
            await self.ensure_voice(ctx)

        return guild_check

    async def ensure_voice(self, ctx):
        """ This check ensures that the bot and command author are in the same voice channel. """
        # Ensure a player exists for this guild
        player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))

        if not ctx.author.voice or not ctx.author.voice.channel:
            raise VoiceCommandError(':raised_hand: | Join a voice channel first.')

        vc = ctx.author.voice.channel
        if not player.is_connected:
            # Bot needs to already be in voice channel to pause, unpause, skip etc.
            if not ctx.command.name in ('play', 'p', 'resetplayer', 'rp'):
                raise VoiceCommandError(':electric_plug: | I\'m not connected to voice.')

            permissions = vc.permissions_for(ctx.me)
            if not permissions.connect or not permissions.speak:
                raise VoiceCommandError(':mute: | I need the `CONNECT` and `SPEAK` permissions.')
            
            if vc.user_limit and vc.user_limit <= len(vc.members):
                raise VoiceCommandError(':mute: | Your voice channel is full.')

            player.store('channel', ctx.channel.id)
            await vc.connect(cls=LavalinkVoiceClient)
        else:
            if int(player.channel_id) != vc.id:
                raise VoiceCommandError(':speaking_head: | You need to be in my voice channel.')

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

        if isinstance(event, TrackStartEvent):
            # Send now playing embed
            await self.now_playing(ctx, title=event.track.title)

            # Store now playing in DB
            self.db.child('player').child(guild_id).child('np').set(event.track.title)
        elif isinstance(event, QueueEndEvent):
            # Queue up the next (valid) track from DB, if any
            queue = self.__get_queue(guild_id)
            while len(queue):
                if await self.enqueue(queue.popleft(), event.player, ctx=ctx, queue_to_db=False, quiet=True):
                    break
            else:
                await self.disconnect(ctx, reason='Queue finished')

            # Save new queue back to DB
            self.__set_queue(guild_id, queue)

    async def enqueue(self, query: str, player: DefaultPlayer, ctx: commands.Context,
                      queue_to_db: bool = False, quiet: bool = False) -> bool:
        # Get the results for the query from Lavalink.
        results = await player.node.get_tracks(query)

        # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
        # Alternatively, results['tracks'] could be an empty array if the query yielded no tracks.
        if not results or not results['tracks']:
            if not quiet:
                await ctx.send(f'Nothing found for `{query}`!')
            return False
        
        # Save to DB if player is not idle.
        queue_to_db = queue_to_db or player.current is not None
        if queue_to_db:
            self.__enqueue(str(ctx.guild.id), query)

        embed = nextcord.Embed(color=nextcord.Color.blurple())

        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL
        #   PLAYLIST_LOADED - direct URL to playlist
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
        if results['loadType'] == 'PLAYLIST_LOADED':
            tracks = results['tracks']

            # Add all of the tracks from the playlist to the queue
            if not queue_to_db:
                for track in tracks:
                    player.add(requester=ctx.author.id, track=track)

            embed.title = 'Playlist enqueued'
            embed.description = f'{results["playlistInfo"]["name"]} - {len(tracks)} tracks'
        else:
            track = results['tracks'][0]
            embed.title = 'Track enqueued'
            embed.description = f'[{track["info"]["title"]}]({track["info"]["uri"]})'

            # Add track to the queue, if the queue is empty.
            if not queue_to_db:
                track = lavalink.models.AudioTrack(track, ctx.author.id)
                player.add(requester=ctx.author.id, track=track)

        if not quiet:
            await ctx.send(embed=embed)

        # We don't want to call .play() if the player is not idle
        # as that will effectively skip the current track.
        if not player.is_playing and not player.paused:
            await player.play()
        
        return True

    @commands.command(aliases=['p'])
    async def play(self, ctx: commands.Context, *, query: str = None):
        """ Searches and plays a song from a given query. """
        async with ctx.typing():
            # Save the context for later
            self.db.child('player').child(str(ctx.guild.id)).child('channel').set(ctx.channel.id)
            self.db.child('player').child(str(ctx.guild.id)).child('message').set(ctx.message.id)

            # Get the player for this guild from cache
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)

            # Pick up where we left off
            if not query:
                old_np = self.db.child('player').child(str(ctx.guild.id)).child('np').get().val()
                if old_np:
                    embed = nextcord.Embed(color=nextcord.Color.purple())
                    embed.title = 'Resuming interrupted queue'
                    embed.description = old_np
                    await ctx.reply(embed=embed)
                    return await self.enqueue(f'ytsearch:{old_np}', player, ctx=ctx, quiet=True)
                return await ctx.reply('Please specify a URL or a search term to play.')

            # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
            query = query.strip('<>')

            # Query is not a URL. Have Lavalink do a YouTube search for it.
            if not check_url(query):
                return await self.enqueue(f'ytsearch:{query}', player, ctx=ctx)

            # Query is a URL.
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
                        # No tracks
                        return await ctx.reply(f'Spotify {sp_type} is empty.')
                    elif len(tracks) == 1:
                        # Single track
                        return await self.enqueue(f'ytsearch:{tracks[0][0]} {tracks[0][1]}', player, ctx=ctx)
                    else:
                        # Multiple tracks
                        # There is no way to queue multiple items in one batch through Lavalink.py,
                        # and performing a search takes time which adds up as playlists grow larger.
                        # Hence, to allow the user to start listening immediately,
                        # we play the first one and store the rest of the queue in DB for later.
                        await ctx.reply(f':arrow_forward: | Enqueueing {sp_type}, this might take a while...')

                        queries = []
                        success = False
                        while len(track_queue):
                            track = track_queue.popleft()
                            track_query = f'ytsearch:{track[0]} {track[1]}'

                            if not success:
                                # Enqueue the first valid track
                                success = await self.enqueue(track_query, player, ctx=ctx, quiet=True)
                                if not success:
                                    await ctx.send(f'Error enqueueing "{track[0]}".')
                            else:
                                # Append the rest to the queue
                                queries.append(track_query)
                        else:
                            if len(queries):
                                # Append everything in one go to save DB accesses
                                self.__enqueue_multiple(str(ctx.guild.id), queries)

                        # Send enqueued embed
                        color = nextcord.Color.blurple()
                        embed = nextcord.Embed(color=color)
                        embed.title = f'Spotify {sp_type} enqueued'
                        embed.description = f'[{list_name}]({query}) by {list_author} ({len(tracks)} tracks)'
                        return await ctx.reply(embed=embed)
            elif check_twitch_url(query) or check_youtube_url(query):
                return await self.enqueue(query, player, ctx=ctx)
            else:
                return await self.enqueue(f'ytsearch:{query}', player, ctx=ctx)

    @commands.command()
    async def pause(self, ctx: commands.Context):
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Pause the player.
        if not player.paused:
            await player.set_pause(pause=True)
            await ctx.reply('Paused the player.')
        else:
            await ctx.reply('Already paused.')
    
    @commands.command()
    async def unpause(self, ctx: commands.Context):
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Unpause the player.
        if player.paused:
            await player.set_pause(pause=False)
            await ctx.reply('Unpaused the player.')
        else:
            await ctx.reply('Already unpaused.')
    
    @commands.command()
    async def skip(self, ctx: commands.Context):
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Get next in queue.
        try:
            async with ctx.typing():
                while True:
                    query = self.__dequeue(player.guild_id)
                    if await self.enqueue(query, player, ctx=ctx, quiet=True):
                        # Skip track.
                        await player.skip()
                        return await ctx.reply('Skipped the track.')
        except QueueEmptyError:
            await ctx.reply('Queue is empty.')
            return await self.disconnect(ctx)

    @commands.command(name='nowplaying', aliases=['np'])
    async def now_playing(self, ctx: commands.Context, title: str = None):
        # Delete the previous now playing message
        try:
            old_message_id = self.db.child('player').child(str(ctx.guild.id)).child('npmessage').get().val()
            if old_message_id:
                old_message = await ctx.fetch_message(int(old_message_id))
                await old_message.delete()
        except Exception as e:
            print(f'Error while trying to delete old npmsg: {e}')

        # Get the player for this guild from cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if player.is_playing or player.paused:
            embed = nextcord.Embed(color=nextcord.Color.teal())
            embed.title = 'Now playing' if player.is_playing else 'Paused'
            embed.description = title if title else player.current.title
        else:
            embed = nextcord.Embed(color=nextcord.Color.yellow())
            embed.title = 'Not playing'
            embed.description = 'To play, use `{0}play <URL/search term>`. Try `{0}help` for more.'.format('rc!')

        # Save this message
        if title:
            message = await ctx.send(embed=embed)
        else:
            message = await ctx.reply(embed=embed)
        self.db.child('player').child(str(ctx.guild.id)).child('npmessage').set(str(message.id))

    @commands.command(aliases=['q'])
    async def queue(self, ctx: commands.Context):
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        await ctx.send(f'Native Lavalink queue: `{player.queue}`')
        try:
            queue = self.__get_queue(str(ctx.guild.id))
            await ctx.send(f'Firebase DB queue: `{ellipsis_truncate(str(queue), 1500)}`')
        except QueueEmptyError:
            await ctx.send(f'Firebase DB queue is empty')
    
    @commands.command(name='clearqueue', aliases=['cq'])
    async def clear_queue(self, ctx: commands.Context):
        # Empty queue in DB
        self.__set_queue(str(ctx.guild.id), deque([]))
        return await ctx.reply(f'**:wastebasket: | Cleared the queue for {ctx.guild.name}**')
    
    @commands.command(name='resetplayer', aliases=['rp'])
    async def reset_player(self, ctx: commands.Context):
        # Delete all traces of the player for this guild from DB
        self.db.child('player').child(str(ctx.guild.id)).remove()
        return await self.disconnect(ctx, reason=f'Reset player state for {ctx.guild.name}')

    @commands.command(aliases=['shuf'])
    async def shuffle(self, ctx: commands.Context):
        try:
            async with ctx.typing():
                queue = self.__get_queue(str(ctx.guild.id))
                shuffle(queue)
                self.__set_queue(str(ctx.guild.id), queue)
            await ctx.reply('Queue shuffled.')
        except QueueEmptyError:
            await ctx.reply('The queue is empty. Nothing to shuffle.')

    @commands.command(aliases=['stop', 'dc'])
    async def disconnect(self, ctx: commands.Context, reason: str = None):
        """ Disconnects the player from the voice channel and clears its queue. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if reason is None:
            if not player.is_connected:
                # We can't disconnect, if we're not connected.
                return await ctx.reply('Not connected.')

            if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
                # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
                # may not disconnect the bot.
                return await ctx.reply('You\'re not in my voice channel!')

            # Clear the queue to ensure old tracks don't start playing
            # when someone else queues something.
            player.queue.clear()

        # Stop the current track so Lavalink consumes less resources.
        await player.stop()

        # Disconnect from the voice channel.
        await ctx.voice_client.disconnect(force=True)
        embed = nextcord.Embed(color=nextcord.Color.blurple())
        embed.title = 'Disconnected from voice'
        embed.description = reason if reason is not None else 'Stopped the player'
        await ctx.send(embed=embed)
