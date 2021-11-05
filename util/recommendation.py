from dataclasses import asdict, dataclass, field
from typing import Dict
from youtubesearchpython import *
from .spotify_client import Spotify
from .string_util import ellipsis_truncate, get_ytid_from_url, parse_spotify_url
from .exception import *

@dataclass
class Recommendation:
    url: str
    recommender: str
    author: str = field(init=False)
    name: str = field(init=False)
    rec_type: str = field(init=False)
    rec_id: str = field(init=False)

def rec_factory(data: Dict):
    safe_keys = {
        'name': 'name',
        'recommender': 'recommender',
        'rec_type': 'type',
        'rec_id': 'id',
        'url': 'url',
        'author': 'author'
    }
    return { safe_keys.get(k): v for k, v in data if k in safe_keys.keys() }

@dataclass
class SpotifyRecommendation(Recommendation):
    spotify: Spotify

    def __post_init__(self):
        # Parse Spotify URL
        entity_type, entity_id = parse_spotify_url(self.url)
        result = None
        author = ""
        if entity_type == 'album':
            result = self.spotify.album(entity_id)
            author = result['artists'][0]['name']
        elif entity_type == 'artist':
            result = self.spotify.artist(entity_id)
        elif entity_type == 'track':
            result = self.spotify.track(entity_id)
            author = result['artists'][0]['name']
        elif entity_type == 'playlist':
            result = self.spotify.playlist(entity_id)
            author = self.spotify.user(result['owner']['id'])['display_name']
        if not result:
            raise SpotifyNotFoundError(entity_type, entity_id)

        self.name = ellipsis_truncate(result['name'])
        self.rec_type = f'spotify-{entity_type}'
        self.rec_id = entity_id
        if entity_type != 'artist':
            self.author = author

@dataclass
class YouTubeRecommendation(Recommendation):
    def __post_init__(self):
        video_id = get_ytid_from_url(self.url)
        if not video_id:
            raise YouTubeInvalidURLError(self.url)

        result = Video.getInfo(video_id, mode=ResultMode.json)
        self.name = result['title']
        self.author = result['channel']['name']
        self.rec_type = 'youtube-video'
        self.rec_id = video_id
