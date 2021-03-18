import re
from .string_util import ellipsis_truncate
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

        ret = {
            "name": ellipsis_truncate(result['name']),
            "type": "spotify-{}".format(entity_type),
            "recommender": recommender,
            "id": entity_id
        }
        if entity_type != 'artist':
            ret["author"] = author
        return ret
