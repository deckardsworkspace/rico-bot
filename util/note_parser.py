from dataclass.note import Note
from datetime import datetime
from typing import Any, Dict, TYPE_CHECKING
from urllib.parse import urlparse
from uuid6 import uuid7
from .enums import NoteType, SpotifyEntityType
from .string_util import check_spotify_url, check_url, parse_spotify_url, reconstruct_url
if TYPE_CHECKING:
    from clients.spotify_client import Spotify
    from spotipy import Spotify as SpotifyClient


def create_spotify_note(client: 'SpotifyClient', uri: str, from_user: int, to_user: int) -> Note:
    # Get entity type and ID
    entity_type, entity_id = parse_spotify_url(uri)

    # Build note title and type
    note_title = uri
    note_type = None
    if entity_type == SpotifyEntityType.ALBUM.value:
        data = client.album(entity_id)
        note_title = f'{data["artists"][0]["name"]} - {data["name"]}'
        note_type = NoteType.SPOTIFY_ALBUM
    elif entity_type == SpotifyEntityType.ARTIST.value:
        data = client.artist(entity_id)
        note_title = data["name"]
        note_type = NoteType.SPOTIFY_ARTIST
    elif entity_type == SpotifyEntityType.PLAYLIST.value:
        data = client.playlist(entity_id, fields='name')
        note_title = data["name"]
        note_type = NoteType.SPOTIFY_PLAYLIST
    elif entity_type == SpotifyEntityType.TRACK.value:
        data = client.track(entity_id)
        note_title = f'{data["artists"][0]["name"]} - {data["name"]}'
        note_type = NoteType.SPOTIFY_TRACK

    # Create recommendation
    return Note(
        id=str(uuid7()),
        timestamp=datetime.now(),
        sender=from_user,
        recipient=to_user,
        type=note_type,
        title=note_title,
        url=reconstruct_url(note_type=note_type.value, note_id=entity_id)
    )


def create_note(spotify: 'Spotify', content: str, from_user: int, to_user: int) -> Note:
    # Is it a URL?
    if check_url(content):
        # Is it a Spotify URL?
        if check_spotify_url(content):
            return create_spotify_note(spotify.client, content, from_user, to_user)
        else:
            # Generic URL
            parsed_url = urlparse(content)
            return Note(
                id=str(uuid7()),
                timestamp=datetime.now(),
                sender=from_user,
                recipient=to_user,
                type=NoteType.URL,
                title=f'Bookmark at {parsed_url.netloc}',
                url=content
            )

    # Not a URL, add as text
    return Note(
        id=str(uuid7()),
        timestamp=datetime.now(),
        sender=from_user,
        recipient=to_user,
        type=NoteType.TEXT,
        title=f'"{content}"',
        url=''
    )


def create_note_from_db(data: Dict[str, Any]) -> Note:
    return Note(
        id=data['id'],
        timestamp=datetime.fromtimestamp(data['timestamp']),
        sender=data['sender'],
        recipient=data['recipient'],
        type=NoteType(data['type']),
        title=data['title'],
        url=data['url']
    )
