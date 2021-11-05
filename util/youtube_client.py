import re
import requests
from .exception import YouTubeInvalidURLError
from .string_util import get_ytid_from_url


class YouTube:
    def __init__(self, api_key):
        self.api_key = api_key

    def match(self, string):
        # https://stackoverflow.com/a/30795206
        return re.match(r"(?:https?://)?(?:youtu\.be/|(?:www\.|m\.)?youtube\.com/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|/))([a-zA-Z0-9_-]+)", string)

    def parse(self, url, recommender):
        video_id = get_ytid_from_url(url)
        if not video_id:
            raise YouTubeInvalidURLError(url)

        params = {
            "part": "snippet",
            "id": video_id,
            "key": self.api_key
        }
        try:
            r = requests.get("https://www.googleapis.com/youtube/v3/videos", params=params)
            snippet = r.json()['items'][0]['snippet']
            return {
                "name": snippet['title'],
                "author": snippet['channelTitle'],
                "type": "youtube-video",
                "recommender": recommender,
                "id": video_id
            }
        except KeyError:
            raise YouTubeInvalidURLError(url)
