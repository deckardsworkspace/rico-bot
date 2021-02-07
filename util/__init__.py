from .spotify_client import create_spotify_client as Spotify
from .spotify_recommendation import SpotifyRecommendation
from .exception import *
from .youtube_recommendation import YouTubeRecommendation


def ellipsis_truncate(string):
    if len(string) < 200:
        return string
    return string[:196] + "..."
