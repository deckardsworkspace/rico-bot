import re
from .exception import *
from urllib.parse import urlparse

valid_paths = ["track", "album", "artist", "playlist"]


class SpotifyRecommendation:
    def __init__(self, spotify):
        self.spotify = spotify

    def match(self, string):
        return re.match(r"(https?://open\.)*spotify(\.com)*[/:]+(track|artist|album|playlist)[/:]+[A-Za-z0-9]+", string)

    def parse(self, string, recommender):
        # Parse string first
        parsed_path = []
        if re.match(r"^https?://open\.spotify\.com", string):
            # We are dealing with a link
            parsed_url = urlparse(string)
            parsed_path = parsed_url.path.split("/")[1:]
        elif re.match(r"^spotify:[a-z]", string):
            # We are dealing with a Spotify uri
            parsed_path = string.split(":")[1:]
        if len(parsed_path) < 2 or parsed_path[0] not in valid_paths:
            raise SpotifyInvalidURLError(string)

        entity_type = parsed_path[0]
        entity_id = parsed_path[1]
        name = None
        if entity_type == 'album':
            result = self.spotify.album(entity_id)
            name = "{0} (Spotify album by {1})".format(result['name'], result['artists'][0]['name'])
        elif entity_type == 'artist':
            result = self.spotify.artist(entity_id)
            name = "{} (Spotify artist)".format(result['name'])
        elif entity_type == 'track':
            result = self.spotify.track(entity_id)
            name = "{0} (Spotify track by {1})".format(result['name'], result['artists'][0]['name'])
        elif entity_type == 'playlist':
            result = self.spotify.playlist(entity_id)
            owner = self.spotify.user(result['owner']['id'])['display_name']
            name = "{0} (Spotify playlist by {1})".format(result['name'], owner)
        if not name:
            raise SpotifyNotFoundError(entity_type, entity_id)

        # Add to recommendation recipients
        desc = "https://open.spotify.com/{0}/{1}\nAdded by {2}".format(entity_type, entity_id, recommender)
        return name, desc
