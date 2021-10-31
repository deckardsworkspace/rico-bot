from __future__ import annotations
from dataclasses import asdict, dataclass
from lavalink.models import AudioTrack, DefaultPlayer
from nextcord import Color, Embed
from nextcord.ext.commands import Bot, Context
from lavalink.models import BasePlayer
from pyrebase.pyrebase import Database
from typing import Dict, List, Optional, Union
from util import QueueEmptyError
from .lavalink import LavalinkVoiceClient
import json


@dataclass
class QueueItem:
    # JSON encoder
    class Encoder(json.JSONEncoder):
        def default(self, o: QueueItem):
            return asdict(o)

    # Who requested the track (required)
    requester: int

    # The Spotify ID for the track
    # If this is not None, title and artist are guaranteed not None too.
    spotify_id: Optional[str] = None

    # Direct track URL (priority 1)
    url: Optional[str] = None

    # Track details (priority 2)
    title: Optional[str] = None
    artist: Optional[str] = None

    # Prefixed search query (priority 3)
    query: Optional[str] = None


# Reconstruct QueueItem from dict
def queue_item_from_dict(d: Dict[str, str]) -> QueueItem:
    required_fields = ['requester', 'spotify_id', 'url', 'title', 'artist', 'query']
    for field in required_fields:
        if field not in d.keys():
            raise ValueError(f'Supplied dict does not have required field {field}')
    
    return QueueItem(
        int(d['requester']),
        d['spotify_id'],
        d['url'],
        d['title'],
        d['artist'],
        d['query']
    )


async def connect_player(player: BasePlayer, bot: Bot, ctx: Context):
    # Are we connected?
    if not player.is_connected:
        # Are we connected according to Discord?
        for client in bot.voice_clients:
            if client.guild is ctx.guild:
                # Remove old connection
                await client.disconnect()

        await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)


async def enqueue(bot: Bot, query: QueueItem, ctx: Context) -> bool:
    # Get the player for this guild from cache
    player = bot.lavalink.player_manager.get(ctx.guild.id)

    # Get the results for the query from Lavalink
    results = await search(player, query)

    # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
    # Alternatively, results['tracks'] could be an empty array if the query yielded no tracks.
    if not results or not results['tracks']:
        embed = Embed(color=Color.red(), title='Nothing found for item', description=query)
        await ctx.send(embed=embed)
        return False

    # If a result is found, connect to voice.
    await connect_player(player, bot, ctx)

    # Valid loadTypes are:
    #   TRACK_LOADED    - single video/direct URL
    #   PLAYLIST_LOADED - direct URL to playlist
    #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
    #   NO_MATCHES      - query yielded no results
    #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
    if results['loadType'] == 'SEARCH_RESULT':
        track = results['tracks'][0]

        # Add Spotify data to track metadata
        if query.spotify_id is not None:
            track['info']['spotify'] = {
                'name': query.title,
                'artist': query.artist,
                'id': query.spotify_id
            }

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

    return True


def enqueue_db(db: Database, guild_id: str, query: List[QueueItem]):
    queue = get_queue_db(db, guild_id)
    queue.extend(query)
    return set_queue_db(db, guild_id, queue)


def dequeue_db(db: Database, guild_id: str, index: Optional[int] = None) -> QueueItem:
    queue = get_queue_db(db, guild_id)
    if not len(queue):
        raise QueueEmptyError()
    return queue[index]


def get_queue_db(db: Database, guild_id: str) -> List[QueueItem]:
    queue_items = db.child('player').child(guild_id).child('queue').get().val()
    if queue_items:
        return [queue_item_from_dict(d) for d in json.loads(queue_items)]
    return []


def get_queue_size(db: Database, guild_id: str) -> int:
    return len(get_queue_db(db, guild_id))


def get_queue_index(db: Database, guild_id: str) -> int:
    return db.child('player').child(guild_id).child('queue_index').get().val()


def set_queue_index(db: Database, guild_id: str, new_index: int):
    return db.child('player').child(guild_id).child('queue_index').set(new_index)


async def search(player: DefaultPlayer, queue_item: QueueItem):
    if queue_item.url is not None:
        # Tell Lavalink to play the URL directly
        query = queue_item.url
    elif queue_item.title is not None:
        # Tell Lavalink to look for the track on YouTube
        query = f'ytsearch:{queue_item.title} {queue_item.artist} audio'
    elif queue_item.query is not None:
        # Tell Lavalink to process the prefixed search query
        query = queue_item.query
    else:
        raise RuntimeError(f'Cannot process incomplete queue item {asdict(queue_item)}')

    return await player.node.get_tracks(query)


def set_queue_db(db: Database, guild_id: str, queue: List[QueueItem]):
    return db.child('player').child(guild_id).child('queue').set(json.dumps(queue, cls=QueueItem.Encoder))
