from lavalink.models import AudioTrack
from nextcord import Color, Embed
from nextcord.ext.commands import BucketType, command, Context, cooldown
from typing import Dict, Optional
from util import create_progress_bar, get_var, human_readable_time, RicoEmbed
from views import NowPlayingView
from .player_helpers import parse_query, send_loop_embed, try_enqueue
from .queue_helpers import (
    dequeue_db, enqueue, enqueue_db, set_queue_db,
    get_queue_size, get_queue_index, set_queue_index,
    get_loop_all, set_loop_all, get_shuffle_indices, set_shuffle_indices
)

@command(name='jump', aliases=['j'])
async def jump_to(self, ctx: Context, *, query: str = None):
    # Jump to a specific track in the queue
    async with ctx.typing():
        # Get the player for this guild from cache.
        player = self.get_player(ctx.guild.id)
        if not player or (not player.is_playing and not player.paused):
            reply = RicoEmbed(title=':stop_button:｜Not currently playing')
            return await reply.send(ctx, as_reply=True)

        # Parse index
        if not query:
            reply = RicoEmbed(title=':x:｜Please specify a track number to jump to')
            return await reply.send(ctx, as_reply=True)
        try:
            index = int(query) - 1
        except ValueError:
            reply = RicoEmbed(title=':x:｜Please specify a valid track number')
            return await reply.send(ctx, as_reply=True)
        
        # Get the queue
        if index < 0 or index >= get_queue_size(self.db, str(ctx.guild.id)):
            reply = RicoEmbed(title=f':x:｜Track number {query} is out of range')
            return await reply.send(ctx, as_reply=True)

        # Play new track
        shuffle_indices = get_shuffle_indices(self.db, ctx.guild.id)
        return await try_enqueue(ctx, self.db, player, shuffle_indices[index] if len(shuffle_indices) > 0 else index, False)


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
    prefix = get_var('BOT_PREFIX')

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
        current_index = 0
        total_tracks = 0
        rec_hint = None
        if not automatic:
            # Invoked by command.
            # Recover track info from player data storage.
            current_id = player.current.identifier
            stored_info = player.fetch(current_id)
            if stored_info and 'title' in stored_info:
                if 'spotify' in stored_info:
                    rec_hint = f'**Like this song?** Save it to your list using `{prefix}rn @mention`.'

                track_info = stored_info
            
            # Get track position   
            current_index = get_queue_index(self.db, str(ctx.guild.id)) + 1
            total_tracks = get_queue_size(self.db, str(ctx.guild.id))

        # If not in storage, recover track info from current track metadata.
        if track_info is None or isinstance(track_info, AudioTrack):
            if track_info is not None and hasattr(track_info, 'identifier'):
                identifier = track_info.identifier
            track_info = {
                'title': player.current.title,
                'author': player.current.author,
                'uri': player.current.uri,
                'isStream': player.current.stream,
                'length': player.current.duration,
                'identifier': identifier
            }
            
        # Don't create progress info for streams
        progress = None
        if not track_info['isStream']:
            # Create progress text
            total_ms = track_info['length']

            # Build progress info
            if automatic:
                h, m, s = human_readable_time(total_ms)
                progress = f'{m} min, {s} sec'
                if h:
                    progress = f'{h} hr, {m} min, {s} sec'
            else:
                elapsed_ms = player.position
                progress = f'**{create_progress_bar(elapsed_ms, total_ms)}**'

        # Show rich track info
        track_name = track_info['title']
        track_artist = track_info['author']
        track_uri = track_info['uri']
        if 'identifier' in track_info:
            # Try to get Spotify track info from cache
            spotify_info = player.fetch(f'{track_info["identifier"]}-spotify', None)
            if spotify_info is not None:
                track_name = spotify_info['name']
                track_artist = spotify_info['artist']
                track_uri = f'https://open.spotify.com/track/{spotify_info["id"]}'

        # Show requester info and avatar
        requester = await self.bot.fetch_user(player.current.requester)
        current_action = 'streaming' if track_info['isStream'] else 'playing'

        # Build embed
        embed_desc = [
            f'**[{track_name}]({track_uri})**',
            f'by **{track_artist}**',
            progress,
            f'\nRequested by {requester.mention}',
            rec_hint
        ]
        if player.repeat:
            embed_desc.append('\n:repeat: **On repeat**\nUse the `loop` command to disable.')
        embed = RicoEmbed(
            color=Color.teal(),
            header='Paused' if player.paused else f'Now {current_action}',
            header_icon_url=requester.display_avatar.url,
            description=embed_desc,
            footer=f'Track {current_index} of {total_tracks}' if not automatic else '',
            timestamp_now=True
        )
    else:
        # Not playing
        embed = RicoEmbed(
            color=Color.yellow(),
            title='Not playing',
            description=[
                f'To play, use `{prefix}play <URL/search term>`',
                f'Try `{prefix}help` for more.'
            ]
        )

    # Send embed with view
    embed = embed.get()
    message = await ctx.send(embed=embed, view=NowPlayingView(ctx, player))

    # Save this message
    self.db.child('player').child(str(ctx.guild.id)).child('npmessage').set(str(message.id))


@command()
async def pause(self, ctx: Context, is_interaction: bool = False) -> Optional[Embed]:
    # Get the player for this guild from cache
    player = self.get_player(ctx.guild.id)

    # Pause the player
    if not player.paused:
        await player.set_pause(pause=True)
        message = 'Paused the player'
    else:
        message = 'Already paused'
    
    # Send reply
    reply = RicoEmbed(title=f':pause_button:｜{message}', color=Color.dark_orange())
    if is_interaction:
        return reply.get()
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
                    cmd = self.bot.get_command('unpause')
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
        new_tracks = await parse_query(ctx, self.spotify, query)
        if len(new_tracks):
            # Add new tracks to queue
            old_size = get_queue_size(self.db, str(ctx.guild.id))
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

            # Are we beginning a new queue?
            if not is_playing:
                # We are! Play the first track.
                set_queue_index(self.db, str(ctx.guild.id), 0)
                await enqueue(self.bot, new_tracks[0], ctx)
            else:
                # We are already playing from a queue.
                # Update shuffle indices if applicable.
                shuffle_indices = get_shuffle_indices(self.db, str(ctx.guild.id))
                if len(shuffle_indices) > 0:
                    # Append new indices to the end of the list
                    new_indices = [old_size + i for i in range(len(new_tracks))]
                    shuffle_indices.extend(new_indices)
                    set_shuffle_indices(self.db, str(ctx.guild.id), shuffle_indices)


@command(aliases=['prev'])
async def previous(self, ctx: Context, is_interaction: bool = False):
    """ Plays the previous track in the queue. """
    cmd = self.bot.get_command('skip')
    return await ctx.invoke(cmd, queue_end=False, forward=False, is_interaction=is_interaction)


@command(aliases=['next'])
async def skip(self, ctx: Context, queue_end: bool = False, forward: bool = True, is_interaction: bool = False):
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
                    if forward:
                        next_i += 1
                    else:
                        next_i -= 1

                # Try playing the track
                if await try_enqueue(ctx, self.db, player, shuffle_indices[next_i] if is_shuffling else next_i, queue_end):
                    # Delete invoker message
                    if not queue_end and not is_interaction:
                        await ctx.message.delete()
                    return

        # Remove player data from DB
        if not queue_end:
            self.db.child('player').child(str(ctx.guild.id)).remove()
            if forward:
                return await self.disconnect(ctx, reason='Reached the end of the queue')
            else:
                embed = RicoEmbed(
                    color=Color.red(),
                    title=':x:｜Already at the start of the queue'
                )
                return await embed.send(ctx, as_reply=True)


@command()
async def unpause(self, ctx: Context, is_interaction: bool = False) -> Optional[Embed]:
    # Get the player for this guild from cache.
    player = self.get_player(ctx.guild.id)

    # Unpause the player.
    if player.paused:
        await player.set_pause(pause=False)
        message = 'Unpaused the player'
    else:
        message = 'Already unpaused'
    
    # Send reply
    reply = RicoEmbed(title=f':arrow_forward:｜{message}', color=Color.dark_green())
    if is_interaction:
        return reply.get()
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
