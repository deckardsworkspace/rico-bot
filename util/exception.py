class SpotifyInvalidURLError(Exception):
    def __init__(self, url):
        self.message = "Invalid Spotify link or URI: {}".format(url)
        super().__init__(self.message)


class SpotifyNotFoundError(Exception):
    def __init__(self, entity_type, entity_id):
        self.message = "No {0} with ID {1} found in Spotify catalog".format(entity_type, entity_id)
        super().__init__(self.message)


class QueueEmptyError(Exception):
    def __init__(self):
        self.message = "Queue is empty."
        super().__init__(self.message)


class VoiceCommandError(Exception):
    def __init__(self, reason):
        self.message = reason
        super().__init__(self.message)


class YouTubeInvalidURLError(Exception):
    def __init__(self, url):
        self.message = "Invalid YouTube video link: {}".format(url)
        super().__init__(self.message)


class YouTubeInvalidPlaylistError(Exception):
    def __init__(self, url):
        self.message = "Invalid YouTube playlist link: {}".format(url)
        super().__init__(self.message)
