from collections import deque
from lavalink.models import AudioTrack, DefaultPlayer
from nextcord import Color, Embed
from nextcord.ext.commands import Bot, Context
from pyrebase.pyrebase import Database
from typing import Deque, Dict, List, Union
from util import QueueEmptyError
from .deque_encoder import DequeEncoder
from .lavalink import LavalinkVoiceClient
import json


async def enqueue(bot: Bot, db: Database, query: Union[str, Dict], ctx: Context,
                  sp_data: dict = None, queue_to_db: bool = None, quiet: bool = False) -> bool:
    # Get the player for this guild from cache
    player = bot.lavalink.player_manager.get(ctx.guild.id)

    # If query is a dict, we must be resuming an old queue
    if isinstance(query, dict):
        # Add directly to player
        if not player.is_connected:
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        player.add(requester=ctx.author.id, track=query)
        return await player.play()

    # Get the results for the query from Lavalink
    results = await search(player, query)

    # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
    # Alternatively, results['tracks'] could be an empty array if the query yielded no tracks.
    if not results or not results['tracks']:
        embed = Embed(color=Color.red(), title='Nothing found for query', description=query)
        await ctx.send(embed=embed)
        return False
    else:
        # If a result is found, connect to voice.
        if not player.is_connected:
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)

    # Save to DB if player is not idle.
    queue_to_db = queue_to_db if queue_to_db is not None else player.current is not None

    embed = Embed(color=Color.blurple())

    # Valid loadTypes are:
    #   TRACK_LOADED    - single video/direct URL
    #   PLAYLIST_LOADED - direct URL to playlist
    #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
    #   NO_MATCHES      - query yielded no results
    #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
    if results['loadType'] == 'PLAYLIST_LOADED':
        tracks = results['tracks']
        for i in range(len(tracks)):
            tracks[i]['requester'] = ctx.author.id

        if queue_to_db:
            # Add all results to database queue
            enqueue_db(db, str(ctx.guild.id), tracks)
        else:
            # Add first track to Lavalink queue...
            if 'identifier' in tracks[0]['info']:
                player.store(tracks[0]['info']['identifier'], tracks[0]['info'])
            player.add(requester=ctx.author.id, track=tracks[0])

            # ...and add the rest to DB queue
            enqueue_db(db, str(ctx.guild.id), tracks[1:])

        embed.title = 'Playlist enqueued'
        embed.description = f'{results["playlistInfo"]["name"]} - {len(tracks)} tracks'
    else:
        track = results['tracks'][0]
        embed.title = 'Track enqueued'
        embed.description = f'[{track["info"]["title"]}]({track["info"]["uri"]})'

        # Add Spotify info to track
        if sp_data is not None:
            track['info']['spotify'] = sp_data

        if queue_to_db:
            # Add track to database queue
            track['requester'] = ctx.author.id
            enqueue_db(db, str(ctx.guild.id), track)
        else:
            # Save track metadata to player storage
            if 'identifier' in track['info']:
                player.store(track['info']['identifier'], track['info'])

            # Add track directly to Lavalink queue
            track = AudioTrack(track, ctx.author.id)
            player.add(requester=ctx.author.id, track=track)

    # We don't want to call .play() if the player is not idle
    # as that will effectively skip the current track.
    if not player.is_playing and not player.paused:
        await player.play()
    if not quiet:
        await ctx.send(embed=embed)

    return True


def enqueue_db(db: Database, guild_id: str, query: Union[str, List[str]]):
    queue = get_queue_db(db, guild_id)

    if isinstance(query, list):
        queue.extend(query)
    else:
        queue.append(query)

    set_queue_db(db, guild_id, queue)


def dequeue_db(db: Database, guild_id: str) -> str:
    queue = get_queue_db(db, guild_id)
    if not len(queue):
        raise QueueEmptyError()

    query = queue.popleft()
    set_queue_db(db, guild_id, queue)
    return query


def get_queue_db(db: Database, guild_id: str) -> Deque[str]:
    queue_items = db.child('player').child(guild_id).child('queue').get().val()
    if queue_items:
        return deque(json.loads(queue_items))
    return deque([])


async def search(player: DefaultPlayer, query: str = None):
    # Get the results for the query from Lavalink
    result = await player.node.get_tracks(query)
    return result


def set_queue_db(db: Database, guild_id: str, queue: Deque[str]):
    db.child('player').child(guild_id).child('queue').set(json.dumps(queue, cls=DequeEncoder))
