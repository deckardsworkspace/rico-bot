from .string_util import ellipsis_truncate, parse_spotify_url
from .exception import *


class SpotifyRecommendation:
    def __init__(self, spotify):
        self.spotify = spotify

    def parse(self, string, recommender):
        # Parse Spotify URL
        entity_type, entity_id = parse_spotify_url(string)
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
