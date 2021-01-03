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
        result = None
        if entity_type == 'album':
            result = self.spotify.album(entity_id)
        elif entity_type == 'artist':
            result = self.spotify.artist(entity_id)
        elif entity_type == 'track':
            result = self.spotify.track(entity_id)
        elif entity_type == 'playlist':
            result = self.spotify.playlist(entity_id)
        if not result:
            raise SpotifyNotFoundError(entity_type, entity_id)

        # Add to recommendation recipients
        name = "{0} (Spotify {1})".format(result['name'], entity_type)
        desc = "https://open.spotify.com/{0}/{1}\nRecommended by {2}".format(entity_type, entity_id, recommender)
        return name, desc
