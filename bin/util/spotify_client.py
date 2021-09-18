import pendulum
import pkce
import requests
import spotipy
import time
import urllib.parse
import uuid
from config import get_var
from ratelimit import limits
from spotipy.oauth2 import SpotifyClientCredentials


def get_chunks(lst):
    # Spotify only allows adding up to 100 tracks at once,
    # so we have to split particularly large playlists into
    # multiple requests.
    for i in range(0, len(lst), 100):
        yield lst[i:i + 100]


class Spotify:
    def __init__(self):
        self.redirect_uri = "https://rico.dantis.me/spotify_auth"
        self.client_id = get_var("SPOTIFY_ID")
        client_secret = get_var("SPOTIFY_SECRET")
        auth_manager = SpotifyClientCredentials(client_id=self.client_id, client_secret=client_secret)
        self.client = spotipy.Spotify(auth_manager=auth_manager)

    def get_client(self):
        return self.client

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
                'playlist-read-collaborative'
            ])
        }
        url = "{}?{}".format(base_url, urllib.parse.urlencode(url_params))

        return url, verifier, state

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
            time.sleep(0.25)              # Rate limit

        # Return new tokens and playlist ID
        return access_token, expires_in, refresh_token, playlist_name, playlist_id

    def get_playlist_cover(self, playlist_id, default=None):
        cover_img = self.client.playlist_cover_image(playlist_id)
        if not len(cover_img):
            return default
        return cover_img[0]['url']
