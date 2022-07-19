class SpotifyInsufficientAccessError(Exception):
    def __init__(self):
        self.message = "Insufficient access to Spotify data. Try authenticating again."
        super().__init__(self.message)

class SpotifyInvalidURLError(Exception):
    def __init__(self, url):
        self.message = "Invalid Spotify link or URI: {}".format(url)
        super().__init__(self.message)


class SpotifyNotFoundError(Exception):
    def __init__(self, entity_type, entity_id):
        self.message = "No {0} with ID {1} found in Spotify catalog".format(entity_type, entity_id)
        super().__init__(self.message)


class YouTubeInvalidURLError(Exception):
    def __init__(self, url, reason=None):
        self.message = f'Invalid YouTube video: {url}. Reason: {reason}'
        super().__init__(self.message)


class YouTubeInvalidPlaylistError(Exception):
    def __init__(self, url, reason=None):
        self.message = f'Invalid YouTube playlist: {url}. Reason: {reason}'
        super().__init__(self.message)
