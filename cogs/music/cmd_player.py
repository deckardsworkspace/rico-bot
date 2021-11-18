from collections import deque
from lavalink.models import AudioTrack
from nextcord import Color
from nextcord.ext.commands import BucketType, command, Context, cooldown
from typing import Dict
from util import (
    check_url, check_spotify_url, create_progress_bar, get_var, human_readable_time,
    parse_spotify_url, RicoEmbed, SpotifyInvalidURLError
)
from .player_helpers import *
from .queue_helpers import (
    dequeue_db, enqueue, enqueue_db, set_queue_db,
    get_queue_size, get_queue_index, set_queue_index,
    get_loop_all, set_loop_all, get_shuffle_indices, QueueItem, set_shuffle_indices
)


@command()
async def loop(self, ctx: Context, *, arg: str = None):
    # Get the player for this guild from cache.
    player = self.get_player(ctx.guild.id)

    message = ''
    if player and (player.is_playing or player.paused):
        if arg == 'all':
            # Loop the whole queue.
            loop_all = get_loop_all(self.db, str(ctx.guild.id))
            set_loop_all(self.db, str(ctx.guild.id), not loop_all)
            if not loop_all:
                message = ':white_check_mark:｜Now looping the whole queue'
            else:
                player.set_repeat(repeat=False)
                message = ':x:｜No longer looping the whole queue'
        elif arg is None:    
            # Loop the current track.
            if not player.repeat:
                player.set_repeat(repeat=True)
                message = ':white_check_mark:｜Now looping the current track'
            else:
                player.set_repeat(repeat=False)
                message = ':x:｜No longer looping the current track'
        else:
            message = f':stop_button:｜Invalid argument {arg}'
    else:
        message = ':stop_button:｜Not currently playing'
    
    # Send reply
    reply = RicoEmbed(title=message)
    return await reply.send(ctx, as_reply=True)


@command(name='nowplaying', aliases=['np'])
async def now_playing(self, ctx: Context, track_info: Dict = None):
    # Delete the previous now playing message
    try:
        old_message_id = self.db.child('player').child(str(ctx.guild.id)).child('npmessage').get().val()
        if old_message_id:
            old_message = await ctx.fetch_message(int(old_message_id))
            await old_message.delete()
    except:
        pass

    # Get the player for this guild from cache
    player = self.get_player(ctx.guild.id)

    if player.is_playing or player.paused:
        automatic = track_info is not None

        # Try to recover track info
        if not automatic:
            # Invoked by command
            current_id = player.current.identifier
            stored_info = player.fetch(current_id)
            if stored_info and 'title' in stored_info:
                track_info = stored_info
        if track_info is None or isinstance(track_info, AudioTrack):
            track_info = {
                'title': player.current.title,
                'author': player.current.author,
                'uri': player.current.uri,
                'isStream': player.current.stream,
                'length': player.current.duration
            }
            
        # Don't create progress info for streams
        progress = None
        if not track_info['isStream']:
            # Create progress text
            total_ms = track_info['length']

            # Build progress info
            if automatic:
                h, m, s = human_readable_time(total_ms)
                progress = f'\n{m} min, {s} sec'
                if h:
                    progress = f'\n{h} hr, {m} min, {s} sec'
            else:
                elapsed_ms = player.position
                progress = f'\n**{create_progress_bar(elapsed_ms, total_ms)}**'

        # Show rich track info
        track_name = track_info['title']
        track_artist = track_info['author']
        track_uri = track_info['uri']
        if hasattr(track_info, 'spotify'):
            track_name = track_info['spotify']['name']
            track_artist = track_info['spotify']['artist']
            track_uri = f'https://open.spotify.com/track/{track_info["spotify"]["id"]}'

        # Show requester info and avatar
        requester = await self.bot.fetch_user(player.current.requester)
        current_action = 'streaming' if track_info['isStream'] else 'playing'

        # Build embed
        embed_desc = [
            f'**[{track_name}]({track_uri})**',
            f'by **{track_artist}**',
            f'requested by {requester.mention}'
        ]
        if progress is not None:
            embed_desc.append(progress)
        if player.repeat:
            embed_desc.append('\n:repeat: **On repeat**\nUse the `loop` command to disable.')
        embed = RicoEmbed(
            color=Color.teal(),
            header='Paused' if player.paused else f'Now {current_action}',
            header_icon_url=requester.display_avatar.url,
            description=embed_desc,
            timestamp_now=True
        )
    else:
        # Not playing
        prefix = get_var('BOT_PREFIX')
        embed = RicoEmbed(
            color=Color.yellow(),
            title='Not playing',
            description=[
                f'To play, use `{prefix}play <URL/search term>`',
                f'Try `{prefix}help` for more.'
            ]
        )

    # Save this message
    message = await embed.send(ctx)
    self.db.child('player').child(str(ctx.guild.id)).child('npmessage').set(str(message.id))


@command()
async def pause(self, ctx: Context):
    # Get the player for this guild from cache
    player = self.get_player(ctx.guild.id)

    # Pause the player
    if not player.paused:
        await player.set_pause(pause=True)
        message = 'Paused the player.'
    else:
        message = 'Already paused.'
    
    # Send reply
    reply = RicoEmbed(title=f':pause_button:｜{message}', color=Color.dark_orange())
    return await reply.send(ctx, as_reply=True)


@command(aliases=['p'])
@cooldown(1, 1, BucketType.guild)
async def play(self, ctx: Context, *, query: str = None):
    """ Searches and plays a song from a given query. """
    async with ctx.typing():
        # Get player from cache
        player = self.get_player(ctx.guild.id)

        # Are we adding to a queue or resuming an old queue?
        is_playing = player is not None and (player.is_playing or player.paused)
        if not query:
            if player.is_connected and is_playing:
                if player.paused:
                    # Unpause the player
                    cmd = self.bot.get_command('pause')
                    return await ctx.invoke(cmd)
                else:
                    # An active player already exists for this guild
                    embed = RicoEmbed(
                        color=Color.red(),
                        title=':x:｜Already playing',
                        description='Use `play <query/URL>` to add to the queue, or use `unpause` to resume playback if paused.'
                    )
                    return await embed.send(ctx, as_reply=True)

            # Try to resume an old queue if it exists
            old_np = get_queue_index(self.db, str(ctx.guild.id))
            if isinstance(old_np, int):
                # Send resuming queue embed
                embed = RicoEmbed(color=Color.purple(), title=':hourglass:｜Resuming interrupted queue')
                await embed.send(ctx, as_reply=True)

                # Play at index
                track = dequeue_db(self.db, str(ctx.guild.id), old_np)
                return await enqueue(self.bot, track, ctx=ctx)
            
            # Old queue does not exist
            embed = RicoEmbed(color=Color.red(), title=':x:｜Specify something to play.')
            return await embed.send(ctx, as_reply=True)
        else:
            # Clear previous queue if not currently playing
            if not is_playing:
                set_queue_db(self.db, str(ctx.guild.id), [])
                set_shuffle_indices(self.db, str(ctx.guild.id), [])

        # Remove leading and trailing <>.
        # <> may be used to suppress embedding links in Discord.
        query = query.strip('<>')
        new_tracks = []
        if check_spotify_url(query):
            # Query is a Spotify URL.
            try:
                sp_type, sp_id = parse_spotify_url(query, valid_types=['track', 'album', 'playlist'])
            except SpotifyInvalidURLError:
                embed = RicoEmbed(
                    color=Color.red(),
                    title=':x:｜Can only play tracks, albums, and playlists from Spotify.'
                )
                return await embed.send(ctx, as_reply=True)

            if sp_type == 'track':
                # Get track details from Spotify
                track_name, track_artist, track_id = self.spotify.get_track(sp_id)

                # Add to database queue
                new_tracks.append(QueueItem(
                    requester=ctx.author.id,
                    title=track_name,
                    artist=track_artist,
                    spotify_id=track_id
                ))
            else:
                # Get playlist or album tracks from Spotify
                list_name, list_author, tracks = self.spotify.get_tracks(sp_type, sp_id)
                track_queue = deque(tracks)

                # Send enqueueing embed
                embed = RicoEmbed(
                    color=Color.green(),
                    header=f'Enqueueing Spotify {sp_type}',
                    title=list_name,
                    description=[
                        f'by [{list_author}]({query})',
                        f'{len(tracks)} track(s)'
                    ],
                    footer='This might take a while, please wait...'
                )
                await embed.send(ctx)

                if len(tracks) < 1:
                    # No tracks
                    return await ctx.reply(f'Spotify {sp_type} is empty.')
                elif len(tracks) == 1:
                    # Single track
                    track_name, track_artist, track_id = tracks[0]
                    new_tracks.append(QueueItem(
                        requester=ctx.author.id,
                        title=track_name,
                        artist=track_artist,
                        spotify_id=track_id
                    ))
                else:
                    # Multiple tracks
                    for track in track_queue:
                        track_name, track_artist, track_id = track
                        new_tracks.append(QueueItem(
                            requester=ctx.author.id,
                            title=track_name,
                            artist=track_artist,
                            spotify_id=track_id
                        ))
        elif check_url(query):
            # Query is a non-Spotify URL.
            new_tracks.append(QueueItem(
                requester=ctx.author.id,
                url=query
            ))
        else:
            # Query is not a URL.
            if query.startswith('ytsearch:') or query.startswith('scsearch:'):
                # Query begins with the search modifiers 'ytsearch' or 'scsearch'
                new_tracks.append(QueueItem(
                    requester=ctx.author.id,
                    query=query
                ))
            else:
                # Have Lavalink do a YouTube search for the query
                new_tracks.append(QueueItem(
                    requester=ctx.author.id,
                    query=f'ytsearch:{query}'
                ))

        if len(new_tracks):
            # Add new tracks to queue
            enqueue_db(self.db, str(ctx.guild.id), new_tracks)

            # Send embed
            first = new_tracks[0]
            first_name = f'**{first.title}**\nby {first.artist}' if first.title is not None else query
            embed = RicoEmbed(
                color=Color.gold(),
                title=':white_check_mark:｜Added to queue',
                description=first_name if len(new_tracks) == 1 else f'{len(new_tracks)} item(s)'
            )
            await embed.send(ctx, as_reply=True)

            # Play the first track
            if not is_playing:
                set_queue_index(self.db, str(ctx.guild.id), 0)
                await enqueue(self.bot, new_tracks[0], ctx)


@command(aliases=['next'])
async def skip(self, ctx: Context, queue_end: bool = False):
    async with ctx.typing():
        # Get the player for this guild from cache.
        player = self.get_player(ctx.guild.id)

        # Queue up the next (valid) track from DB, if any
        current_i = get_queue_index(self.db, str(ctx.guild.id))
        loop_all = get_loop_all(self.db, str(ctx.guild.id))
        if isinstance(current_i, int):
            # Are we shuffling?
            shuffle_indices = get_shuffle_indices(self.db, str(ctx.guild.id))
            is_shuffling = len(shuffle_indices) > 0

            # Set initial index
            queue_size = get_queue_size(self.db, str(ctx.guild.id))
            next_i = shuffle_indices.index(current_i) if is_shuffling else current_i
            while next_i < queue_size:
                # Have we reached the end of the queue?
                if next_i == queue_size - 1:
                    # Reached the end of the queue, are we looping?
                    if loop_all:
                        await send_loop_embed(ctx)
                        next_i = 0
                    else:
                        # We are not looping
                        break
                else:
                    next_i += 1

                # Try playing the track
                if await try_enqueue(ctx, self.db, player, shuffle_indices[next_i] if is_shuffling else next_i, queue_end):
                    return

        # Remove player data from DB
        if not queue_end:
            self.db.child('player').child(str(ctx.guild.id)).remove()
            return await self.disconnect(ctx, reason='Reached the end of the queue')


@command()
async def unpause(self, ctx: Context):
    # Get the player for this guild from cache.
    player = self.get_player(ctx.guild.id)

    # Unpause the player.
    if player.paused:
        await player.set_pause(pause=False)
        message = 'Unpaused the player.'
    else:
        message = 'Already unpaused.'
    
    # Send reply
    reply = RicoEmbed(title=f':arrow_forward:｜{message}', color=Color.dark_green())
    return await reply.send(ctx, as_reply=True)


@command(aliases=['v', 'vol'])
async def volume(self, ctx: Context, *, vol: str = None):
    # Get the player for this guild from cache
    player = self.get_player(ctx.guild.id)

    if vol is None:
        if player is not None:
            # Return current player volume
            embed = RicoEmbed(
                color=Color.dark_grey(),
                title=f':loud_sound:｜Volume is currently at {player.volume}',
                description=f'To set, use `{get_var("BOT_PREFIX")}{ctx.invoked_with} <int>`.'
            )
            return await embed.send(ctx)

    if player is not None and player.is_playing and not player.paused:
        try:
            new_vol = int(vol)
            if new_vol < 0 or new_vol > 1000:
                raise ValueError
        except ValueError:
            embed = RicoEmbed(
                color=Color.red(),
                title=f':x:｜Invalid volume `{vol}`',
                description='Please specify an integer between 0 and 1000, inclusive.'
            )
            return await embed.send(ctx)

        await player.set_volume(new_vol)
        embed = RicoEmbed(
            color=Color.dark_grey(),
            title=f':white_check_mark:｜Volume set to {new_vol}',
        )
        return await embed.send(ctx)
    
    # Not playing
    embed = RicoEmbed(
        color=Color.red(),
        title=':x:｜Player is not playing or is paused',
    )
    return await embed.send(ctx)
