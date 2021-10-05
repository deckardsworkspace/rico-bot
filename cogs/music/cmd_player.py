from collections import deque
from math import ceil, floor
from nextcord import Color, Embed
from nextcord.ext.commands import command, Context
from typing import Dict, Union
from util import check_url, check_spotify_url, check_twitch_url, get_var, parse_spotify_url
from util import SpotifyInvalidURLError
from .queue_helpers import enqueue, enqueue_db, get_queue_db, set_queue_db


@command(name='nowplaying', aliases=['np'])
async def now_playing(self, ctx: Context, track_info: Dict = None):
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
        embed = Embed(color=Color.teal())
        embed.title = 'Paused' if player.paused else 'Now playing'
        embed.description = player.current.title

        # Get requester info
        requester = await self.bot.fetch_user(player.current.requester)
        embed.set_footer(text=f'Requested by {requester.name}#{requester.discriminator}')

        # Try to recover track info
        progress = None
        if track_info is None:
            # Invoked by command
            current_id = player.current.identifier
            stored_info = player.fetch(current_id)
            if stored_info and 'title' in stored_info:
                track_info = stored_info

                # Don't create progress info for Twitch streams
                if not check_twitch_url(track_info['uri']):
                    # Create progress text
                    total_ms = track_info['length']
                    total_m, total_s = divmod(floor(total_ms / 1000), 60)
                    total_text = f'{total_m:02d}:{total_s:02d}'
                    elapsed_ms = player.position
                    elapsed_m, elapsed_s = divmod(floor(elapsed_ms / 1000), 60)
                    elapsed_text = f'{elapsed_m:02d}:{elapsed_s:02d}'

                    # Create progress bar
                    total = 20
                    elapsed_perc = elapsed_ms / total_ms
                    elapsed = '-' * (ceil(elapsed_perc * total) - 1)
                    remain = ' ' * floor((1 - elapsed_perc) * total)
                    progress_bar = f'`[{elapsed}O{remain}]`'

                    # Build progress info
                    progress = f'\n**{elapsed_text} {progress_bar} {total_text}**'
        else:
            # Invoked by listener
            # Don't create progress info for Twitch streams
            if check_twitch_url(track_info['uri']):
                m, s = divmod(floor(track_info['length'] / 1000), 60)
                progress = f'{m:02d} min, {s:02d} sec'

        # Show rich track info
        track_name = track_info['title']
        track_artist = track_info['author']
        track_uri = track_info['uri']
        if hasattr(track_info, 'spotify'):
            track_name = track_info['spotify']['name']
            track_artist = track_info['spotify']['artist']
            track_uri = f'https://open.spotify.com/track/{track_info["spotify"]["id"]}'
        embed.description = '\n'.join([
            f'**[{track_name}]({track_uri})**',
            f'by {track_artist}',
            progress if progress is not None else ''
        ])

    else:
        embed = Embed(color=Color.yellow())
        embed.title = 'Not playing'
        embed.description = 'To play, use `{0}play <URL/search term>`. Try `{0}help` for more.'.format(get_var('BOT_PREFIX'))

    # Save this message
    if track_info is not None:
        message = await ctx.send(embed=embed)
    else:
        message = await ctx.reply(embed=embed)
    self.db.child('player').child(str(ctx.guild.id)).child('npmessage').set(str(message.id))


@command()
async def pause(self, ctx: Context):
    # Get the player for this guild from cache.
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)

    # Pause the player.
    if not player.paused:
        await player.set_pause(pause=True)
        await ctx.reply('Paused the player.')
    else:
        await ctx.reply('Already paused.')


@command(aliases=['p'])
async def play(self, ctx: Context, *, query: str = None):
    """ Searches and plays a song from a given query. """
    async with ctx.typing():
        if not query:
            # Pick up where we left off
            old_np = self.db.child('player').child(str(ctx.guild.id)).child('np').get().val()
            if old_np:
                # Send resuming queue embed
                embed = Embed(color=Color.purple(), title='Resuming interrupted queue')
                await ctx.reply(embed=embed)

                # Reconstruct track object
                decoded = await self.bot.lavalink.decode_track(old_np)
                track = {
                    'track': old_np,
                    'info': decoded
                }
                return await enqueue(self.bot, self.db, track, ctx=ctx, quiet=True)
            return await ctx.reply('Please specify a URL or a search term to play.')
        else:
            # Clear previous queue if not currently playing
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            if player is not None and not (player.is_playing or player.paused):
                set_queue_db(self.db, str(ctx.guild.id), deque([]))

        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip('<>')
        if check_spotify_url(query):
            # Query is a Spotify URL.
            try:
                sp_type, sp_id = parse_spotify_url(query, valid_types=['track', 'album', 'playlist'])
            except SpotifyInvalidURLError:
                return await ctx.reply('Only Spotify track, album, and playlist URLs are supported.')

            if sp_type == 'track':
                # Get track details from Spotify
                track_name, track_artist, track_id = self.spotify.get_track(sp_id)
                return await enqueue(self.bot, self.db, f'ytsearch:{track_name} {track_artist} audio', ctx=ctx, sp_data={
                    'name': track_name, 'artist': track_artist, 'id': track_id
                })
            else:
                # Get playlist or album tracks from Spotify
                list_name, list_author, tracks = self.spotify.get_tracks(sp_type, sp_id)
                track_queue = deque(tracks)

                if len(tracks) < 1:
                    # No tracks
                    return await ctx.reply(f'Spotify {sp_type} is empty.')
                elif len(tracks) == 1:
                    # Single track
                    track_name, track_artist, track_id = tracks[0]
                    return await enqueue(self.bot, self.db, f'ytsearch{track_name} {track_artist} audio', ctx=ctx, sp_data={
                        'name': track_name, 'artist': track_artist, 'id': track_id
                    })
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
                        track_name, track_artist, track_id = track
                        track_query = f'ytsearch:{track_name} {track_artist} audio'

                        if not success:
                            # Enqueue the first valid track
                            success = await enqueue(self.bot, self.db, track_query, ctx=ctx, quiet=True, sp_data={
                                'name': track_name, 'artist': track_artist, 'id': track_id
                            })
                        else:
                            # Append to db queue
                            track_obj = {
                                'requester': ctx.author.id,
                                'spotify': {
                                    'name': track_name,
                                    'artist': track_artist,
                                    'id': track_id
                                }
                            }
                            queries.append(track_obj)
                    else:
                        if len(queries):
                            # Append everything in one go to save DB accesses
                            enqueue_db(self.db, str(ctx.guild.id), queries)

                    # Send enqueued embed
                    embed = Embed(color=Color.blurple())
                    embed.title = f'Spotify {sp_type} enqueued'
                    embed.description = f'[{list_name}]({query}) by {list_author} ({len(tracks)} tracks)'
                    return await ctx.reply(embed=embed)
        elif check_url(query) or query.startswith('ytsearch:') or query.startswith('scsearch:'):
            # Query is a non-Spotify URL, or begins with the search modifiers 'ytsearch' or 'scsearch'
            return await enqueue(self.bot, self.db, query, ctx=ctx)
        else:
            # Query is not a URL. Have Lavalink do a YouTube search for it.
            return await enqueue(self.bot, self.db, f'ytsearch:{query} audio', ctx=ctx)


@command(aliases=['next'])
async def skip(self, ctx: Context, queue_end: bool = False):
    async with ctx.typing():
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Queue up the next (valid) track from DB, if any
        queue = get_queue_db(self.db, str(ctx.guild.id))
        while len(queue):
            track = queue.popleft()
            try:
                if 'spotify' in track:
                    # Perform query
                    track_name = track["spotify"]["name"]
                    track_artist = track["spotify"]["artist"]
                    query = f'ytsearch:{track_name} {track_artist} audio'
                    if await enqueue(self.bot, self.db, query, ctx=ctx, quiet=True,
                                     sp_data=track['spotify'], queue_to_db=False):
                        if not queue_end:
                            await player.skip()
                        break
                elif 'info' in track:
                    # Save track metadata to player storage
                    if 'identifier' in track['info']:
                        player.store(track['info']['identifier'], track['info'])

                    # Play track
                    player.add(requester=track['requester'], track=track)
                    await player.play()
                    break
                else:
                    raise Exception('Track object is incomplete')
            except Exception as e:
                await ctx.send(f'Unable to play {track}. Reason: {e}')
                continue
        else:
            if not queue_end:
                # Remove now playing data from DB
                self.db.child('player').child(str(ctx.guild.id)).child('np').remove()
                await self.disconnect(ctx, reason='Reached the end of the queue')

        # Save new queue back to DB
        set_queue_db(self.db, str(ctx.guild.id), queue)


@command()
async def unpause(self, ctx: Context):
    # Get the player for this guild from cache.
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)

    # Unpause the player.
    if player.paused:
        await player.set_pause(pause=False)
        await ctx.reply('Unpaused the player.')
    else:
        await ctx.reply('Already unpaused.')


@command(aliases=['v', 'vol'])
async def volume(self, ctx: Context, *, vol: str = None):
    if vol is None:
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player is not None:
            # Return current player volume
            embed = Embed(color=Color.purple())
            embed.title = f':loud_sound: Volume is currently at {player.volume}'
            embed.description = f'To set, use `{get_var("BOT_PREFIX")}{ctx.invoked_with} <int>`.'
            return await ctx.reply(embed=embed)
        return await ctx.reply(f'No active players in {ctx.guild.name}')

    try:
        new_vol = int(vol)
        if new_vol < 0 or new_vol > 1000:
            raise ValueError
    except ValueError:
        return await ctx.reply('Please specify an integer between 0 and 1000, inclusive.')
    
    # Get the player for this guild from cache.
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)
    if player is not None and player.is_playing and not player.paused:
        await player.set_volume(new_vol)
        return await ctx.reply(f':white_check_mark: Volume set to **{new_vol}**')
    return await ctx.reply('Player is not playing or is paused')
