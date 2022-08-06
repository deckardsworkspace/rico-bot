from enum import Enum


class RecommendationType(Enum):
    SPOTIFY_ALBUM = 'spotify:album'
    SPOTIFY_ARTIST = 'spotify:artist'
    SPOTIFY_PLAYLIST = 'spotify:playlist'
    SPOTIFY_TRACK = 'spotify:track'
    TEXT = 'text'
    YOUTUBE = 'youtube'


class SpotifyEntityType(Enum):
    ALBUM = 'album'
    ARTIST = 'artist'
    PLAYLIST = 'playlist'
    TRACK = 'track'
