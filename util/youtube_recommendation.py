import re
import requests
from urllib.parse import urlparse, parse_qs
from .exception import YouTubeInvalidURLError


def get_id_from_url(url):
    # https://gist.github.com/kmonsoor/2a1afba4ee127cce50a0
    if url.startswith(('youtu', 'www')):
        url = 'http://' + url

    query = urlparse(url)
    if 'youtube' in query.hostname:
        if re.match(r"^/watch", query.path):
            if len(query.query):
                return parse_qs(query.query)['v'][0]
            else:
                return query.path.split("/")[2]
        elif query.path.startswith(('/embed/', '/v/')):
            return query.path.split('/')[2]
    elif 'youtu.be' in query.hostname:
        return query.path[1:]
    else:
        raise YouTubeInvalidURLError(url)


class YouTubeRecommendation:
    def __init__(self, api_key):
        self.api_key = api_key

    def match(self, string):
        # https://stackoverflow.com/a/30795206
        return re.match(r"(?:https?://)?(?:youtu\.be/|(?:www\.|m\.)?youtube\.com/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|/))([a-zA-Z0-9_-]+)", string)

    def parse(self, url, recommender):
        video_id = get_id_from_url(url)
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
            name = snippet['title']
            desc = ("YouTube video by {0}\n"
                    "https://youtube.com/watch/{1}\n"
                    "Added by {2}").format(snippet['channelTitle'], video_id, recommender)
            return name, desc
        except KeyError:
            raise YouTubeInvalidURLError(url)
