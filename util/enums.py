from enum import Enum


class NoteType(Enum):
    SPOTIFY_ALBUM = 'spotify:album'
    SPOTIFY_ARTIST = 'spotify:artist'
    SPOTIFY_PLAYLIST = 'spotify:playlist'
    SPOTIFY_TRACK = 'spotify:track'
    TEXT = 'text'
    URL = 'url'
    YOUTUBE = 'youtube'


class SpotifyEntityType(Enum):
    ALBUM = 'album'
    ARTIST = 'artist'
    PLAYLIST = 'playlist'
    TRACK = 'track'
