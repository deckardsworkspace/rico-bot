import spotipy
from config import get_var
from spotipy.oauth2 import SpotifyClientCredentials


def create_spotify_client():
    auth_manager = SpotifyClientCredentials(client_id=get_var("SPOTIFY_ID"), client_secret=get_var("SPOTIFY_SECRET"))
    return spotipy.Spotify(auth_manager=auth_manager)
