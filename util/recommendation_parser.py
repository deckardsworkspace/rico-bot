from dataclass.recommendation import Recommendation
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid6 import uuid7
from .enums import RecommendationType, SpotifyEntityType
from .string_util import check_spotify_url, check_url, parse_spotify_url, reconstruct_url
if TYPE_CHECKING:
    from clients.spotify_client import Spotify
    from spotipy import Spotify as SpotifyClient


def create_spotify_recommendation(client: 'SpotifyClient', uri: str, from_user: int, to_user: int) -> Recommendation:
    # Get entity type and ID
    entity_type, entity_id = parse_spotify_url(uri)

    # Create recommendation title and type
    rec_title = uri
    rec_type = None
    if entity_type == SpotifyEntityType.ALBUM.value:
        data = client.album(entity_id)
        rec_title = f'{data["artists"][0]["name"]} - {data["name"]}'
        rec_type = RecommendationType.SPOTIFY_ALBUM
    elif entity_type == SpotifyEntityType.ARTIST.value:
        data = client.artist(entity_id)
        rec_title = data["name"]
        rec_type = RecommendationType.SPOTIFY_ARTIST
    elif entity_type == SpotifyEntityType.PLAYLIST.value:
        data = client.playlist(entity_id, fields='name')
        rec_title = data["name"]
        rec_type = RecommendationType.SPOTIFY_PLAYLIST
    elif entity_type == SpotifyEntityType.TRACK.value:
        data = client.track(entity_id)
        rec_title = f'{data["artists"][0]["name"]} - {data["name"]}'
        rec_type = RecommendationType.SPOTIFY_TRACK

    # Create recommendation
    return Recommendation(
        id=str(uuid7()),
        timestamp=datetime.now(),
        recommendee=to_user,
        recommender=from_user,
        type=rec_type,
        title=rec_title,
        url=reconstruct_url(rec_type=rec_type.value, rec_id=entity_id)
    )


def parse_recommendation(spotify: 'Spotify', recommendation: str, from_user: int, to_user: int) -> Recommendation:
    # Is it a URL?
    if check_url(recommendation):
        # Is it a Spotify URL?
        if check_spotify_url(recommendation):
            return create_spotify_recommendation(spotify.client, recommendation, from_user, to_user)
        else:
            # Generic URL
            parsed_url = urlparse(recommendation)
            return Recommendation(
                id=str(uuid7()),
                timestamp=datetime.now(),
                recommendee=to_user,
                recommender=from_user,
                type=RecommendationType.URL,
                title=f'Bookmark at {parsed_url.netloc}',
                url=recommendation
            )

    # Not a URL, add as text recommendation
    return Recommendation(
        id=str(uuid7()),
        timestamp=datetime.now(),
        recommendee=to_user,
        recommender=from_user,
        type=RecommendationType.TEXT,
        title=f'"{recommendation}"',
        url=''
    )
