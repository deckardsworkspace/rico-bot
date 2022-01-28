import pendulum
import pkce
import requests
import spotipy
import time
import urllib.parse
import uuid
from .config import get_var
from .exception import SpotifyInvalidURLError
from ratelimit import limits
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Dict, List, Tuple


def get_chunks(lst):
    # Spotify only allows adding up to 100 tracks at once,
    # so we have to split particularly large playlists into
    # multiple requests.
    for i in range(0, len(lst), 100):
        yield lst[i:i + 100]


def extract_track_info(track_obj) -> tuple[str, str]:
    if 'track' in track_obj:
        # Nested track (playlist track object)
        track_obj = track_obj['track']
    return (
        track_obj['name'],
        track_obj['artists'][0]['name'],
        track_obj['id'],
        int(track_obj['duration_ms'])
    )


class Spotify:
    def __init__(self):
        self.redirect_uri = "https://rico.dantis.me/spotify_auth"
        self.client_id = get_var("SPOTIFY_ID")
        client_secret = get_var("SPOTIFY_SECRET")
        auth_manager = SpotifyClientCredentials(client_id=self.client_id, client_secret=client_secret)
        self.client = spotipy.Spotify(auth_manager=auth_manager)

    def create_auth_url(self):
        # Create code challenge and verifier
        verifier, challenge = pkce.generate_pkce_pair(128)

        # Create state token (RFC 6749)
        state = str(uuid.uuid4())

        # Construct authorization URI
        base_url = "https://accounts.spotify.com/authorize"
        url_params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "code_challenge_method": "S256",
            "code_challenge": challenge,
            "state": state,
            "scope": ' '.join([
                'playlist-modify-public',
                'playlist-modify-private',
                'playlist-read-private',
                'playlist-read-collaborative',
                'user-read-recently-played'
            ])
        }
        url = "{}?{}".format(base_url, urllib.parse.urlencode(url_params))

        return url, verifier, state

    @limits(calls=10, period=5)
    def create_playlist(self, token_data, username, tracks):
        # Check if the token is almost expired (within 15 sec)
        access_token = token_data['access_token']
        refresh_token = token_data['refresh_token']
        expires_in = int(token_data['expires_in'])
        if int(time.time()) + 15 >= expires_in:
            # Request new token
            access_token, expires_in, refresh_token = self.request_token(refresh_token=refresh_token)

        # Who are we?
        profile_req = requests.get("https://api.spotify.com/v1/me", headers={
            "Authorization": "Bearer {}".format(access_token)
        })
        if profile_req.status_code != 200:
            profile_req.raise_for_status()
        user_id = profile_req.json()['id']

        # Create playlist
        playlist_headers = {
            "Authorization": "Bearer {}".format(access_token),
            "Content-Type": "application/json"
        }
        create_params = {
            "name": "Rico dump ({})".format(pendulum.now('Asia/Manila').to_formatted_date_string()),
            "public": False,
            "collaborative": False,
            "description": "Songs recommended to {} through Rico the Discord bot".format(username)
        }
        create_url = "https://api.spotify.com/v1/users/{}/playlists".format(user_id)
        create_req = requests.post(create_url, json=create_params, headers=playlist_headers)
        if create_req.status_code not in [200, 201]:
            create_req.raise_for_status()
        playlist_name = create_req.json()['name']
        playlist_id = create_req.json()['id']

        # Add tracks to playlist
        add_url = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)
        chunked_tracks = list(get_chunks(tracks))
        for chunk in chunked_tracks:
            add_params = {"uris": chunk}
            add_req = requests.post(add_url, json=add_params, headers=playlist_headers)
            if add_req.status_code != 200:
                add_req.raise_for_status()
            time.sleep(0.25)  # Rate limit

        # Return new tokens and playlist ID
        return access_token, expires_in, refresh_token, playlist_name, playlist_id

    def get_client(self):
        return self.client
    
    def __get_art(self, art: List[Dict[str, str]], default='') -> str:
        if not len(art):
            return default
        return art[0]['url']
    
    def get_album_art(self, album_id: str) -> str:
        return self.__get_art(self.client.album(album_id)['images'])
    
    def get_artist_image(self, artist_id: str) -> str:
        return self.__get_art(self.client.artist(artist_id)['images'])

    def get_playlist_cover(self, playlist_id: str, default: str) -> str:
        return self.__get_art(self.client.playlist_cover_image(playlist_id), default=default)
    
    def get_track_art(self, track_id: str) -> str:
        return self.__get_art(self.client.track(track_id)['album']['images'])

    def get_track(self, track_id: str) -> tuple[str, str]:
        return extract_track_info(self.client.track(track_id))

    def get_tracks(self, list_type: str, list_id: str) -> Tuple[str, str, List[Tuple[str, str, str, int]]]:
        offset = 0
        tracks = []

        # Get list name and author
        if list_type == 'album':
            album_info = self.client.album(list_id)
            list_name = album_info['name']
            list_author = album_info['artists'][0]['name']
        elif list_type == 'playlist':
            playlist_info = self.client.playlist(list_id, fields='name,owner.display_name')
            list_name = playlist_info['name']
            list_author = playlist_info['owner']['display_name']
        else:
            raise SpotifyInvalidURLError(f'spotify:{list_type}:{list_id}')

        # Get tracks
        while True:
            if list_type == 'album':
                response = self.client.album_tracks(list_id, offset=offset)
            else:
                fields = 'items.track.name,items.track.artists,items.track.id,items.track.duration_ms'
                response = self.client.playlist_items(list_id, offset=offset,
                                                      fields=fields,
                                                      additional_types=['track'])

            if len(response['items']) == 0:
                break

            tracks.extend(response['items'])
            offset = offset + len(response['items'])

        return list_name, list_author, list(map(extract_track_info, tracks))

    def request_token(self, code=None, verifier=None, refresh_token=None):
        # Perform POST request
        if refresh_token is not None:
            req_params = {
                "client_id": self.client_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
        else:
            req_params = {
                "client_id": self.client_id,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": verifier
            }
        req_url = "https://accounts.spotify.com/api/token"
        req = requests.post(req_url, data=req_params)

        # Check if request is OK
        if req.status_code != 200:
            req.raise_for_status()

        # Return data
        current_time = int(time.time())
        access_token = req.json()['access_token']
        expires_in = current_time + req.json()['expires_in']
        new_refresh_token = req.json()['refresh_token']
        return access_token, expires_in, new_refresh_token
