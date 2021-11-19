from asyncio import TimeoutError
from collections import deque
from dataclasses import dataclass
from lavalink.models import BasePlayer
from nextcord import Color, Member, Reaction
from nextcord.ext.commands import Context
from pyrebase.pyrebase import Database
from typing import List
from util import (
    check_url, check_spotify_url, get_youtube_matches, human_readable_time,
    parse_spotify_url, RicoEmbed, Spotify, SpotifyInvalidURLError
)
from .queue_helpers import QueueItem, enqueue, dequeue_db, set_queue_index


async def parse_query(ctx: Context, spotify: Spotify, query: str) -> List[QueueItem]:
    if check_url(query):
        return await parse_query_url(ctx, spotify, query)

    # Query is not a URL. Do a YouTube search for the query and allow user to choose.
    result_emojis = ('1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟')
    results = get_youtube_matches(query)
    result_fields = []
    for i, result in enumerate(results):
        h, m, s = human_readable_time(result.duration_ms)
        duration = f'{h}h {m}m {s}s' if h > 0 else f'{m}m {s}s'
        result_fields.append([
            f'{result_emojis[i]} {result.title}',
            f'by [{result.author}]({result.url})\n{duration}'
        ])
    result_embed = RicoEmbed(
        title=f'Search results',
        description=f'for "{query}"',
        color=Color.orange(),
        footer='Select a result by clicking the corresponding emoji.',
        fields=result_fields
    )
    message = await result_embed.send(ctx)
    
    # Add reactions to the message
    for i, emoji in enumerate(result_emojis):
        await message.add_reaction(emoji)

    # Wait for user to react
    def check(r: Reaction, u: Member):
        return u == ctx.author and str(r.emoji) in result_emojis
    try:
        r, _ = await ctx.bot.wait_for('reaction_add', check=check, timeout=60.0)
    except TimeoutError:
        # Remove all reactions to the message
        await message.clear_reactions()
        return []
    else:
        # Delete message
        await message.delete()
        result = results[result_emojis.index(r.emoji)]
        return [QueueItem(
            title=result.title,
            artist=result.author,
            requester=ctx.author.id,
            url=result.url
        )]


async def parse_query_url(ctx: Context, spotify: Spotify, query: str) -> List[QueueItem]:
    if check_spotify_url(query):
        # Query is a Spotify URL.
        return await parse_spotify_query(ctx, spotify, query)

    # Query is a non-Spotify URL.
    return [QueueItem(
        requester=ctx.author.id,
        url=query
    )]


async def parse_spotify_query(ctx: Context, spotify: Spotify, query: str) -> List[QueueItem]:
    # Generally for Spotify tracks, we pick the YouTube result with
    # the same artist and title, and the closest duration to the Spotify track.
    try:
        sp_type, sp_id = parse_spotify_url(query, valid_types=['track', 'album', 'playlist'])
    except SpotifyInvalidURLError:
        embed = RicoEmbed(
            color=Color.red(),
            title=':x:｜Can only play tracks, albums, and playlists from Spotify.'
        )
        return await embed.send(ctx, as_reply=True)

    new_tracks = []
    if sp_type == 'track':
        # Get track details from Spotify
        track_queue = [spotify.get_track(sp_id)]
    else:
        # Get playlist or album tracks from Spotify
        list_name, list_author, tracks = spotify.get_tracks(sp_type, sp_id)
        track_queue = deque(tracks)

    if len(track_queue) < 1:
        # No tracks
        return await ctx.reply(f'Spotify {sp_type} is empty.')
    else:
        # At least one track.
        # Send embed if the list is longer than 1 track.
        if len(track_queue) > 1:
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

        for track in track_queue:
            track_name, track_artist, track_id, track_duration = track

            # Add to database queue
            new_tracks.append(QueueItem(
                requester=ctx.author.id,
                title=track_name,
                artist=track_artist,
                spotify_id=track_id,
                duration=track_duration
            ))
    
    return new_tracks


async def send_loop_embed(ctx: Context):
    embed = RicoEmbed(
        color=Color.dark_green(),
        title=f':repeat:｜Looping back to the start',
        description=[
            'Reached the end of the queue.',
            f'Use the `loop all` command to disable.'
        ]
    )
    await embed.send(ctx)


async def try_enqueue(ctx: Context, db: Database, player: BasePlayer, track_index: int, queue_end: bool) -> bool:
    track = dequeue_db(db, str(ctx.guild.id), track_index)
    try:
        if await enqueue(ctx.bot, track, ctx=ctx):
            if not queue_end:
                await player.skip()

            # Save new queue index back to db
            set_queue_index(db, str(ctx.guild.id), track_index)
            return True
    except Exception as e:
        embed = RicoEmbed(
            color=Color.red(),
            title=f':x:｜Unable to play track',
            description=[
                f'Track: `{track}`'
                f'Reason: `{e}`'
            ]
        )
        await embed.send(ctx)
    return False
