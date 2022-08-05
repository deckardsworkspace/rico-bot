from typing import Tuple, Union
import validators
import re
from math import ceil, floor, log, pow
from urllib.parse import urlparse, parse_qs
from .exceptions import *


def check_ip_addr(url: str) -> bool:
    return validators.ipv4(url) or validators.ipv6(url)


def check_url(url: str) -> bool:
    return validators.domain(url) or validators.url(url)


def check_spotify_url(url: str) -> bool:
    url_regex = r"(https?://open\.)*spotify(\.com)*[/:]+(track|artist|album|playlist)[/:]+[A-Za-z0-9]+"
    return re.match(url_regex, url) is not None


def check_youtube_url(url: str) -> bool:
    url_regex = r"(?:https?://)?(?:youtu\.be/|(?:www\.|m\.)?youtube\.com/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|/))([a-zA-Z0-9_-]+)"
    return re.match(url_regex, url) is not None


def ellipsis_truncate(string: str, length: int = 200) -> str:
    if len(string) < length:
        return string
    return string[:length - 4] + "..."


def get_ytid_from_url(url, id_type: str = 'v') -> str:
    # https://gist.github.com/kmonsoor/2a1afba4ee127cce50a0
    if not check_youtube_url(url):
        raise YouTubeInvalidURLError(url)

    if url.startswith(('youtu', 'www')):
        url = 'http://' + url

    query = urlparse(url)
    if 'youtube' in query.hostname:
        if re.match(r"^/watch", query.path):
            if len(query.query):
                return parse_qs(query.query)[id_type][0]
            return query.path.split("/")[2]
        elif query.path.startswith(('/embed/', '/v/')):
            return query.path.split('/')[2]
    elif 'youtu.be' in query.hostname:
        return query.path[1:]
    
    raise YouTubeInvalidURLError(url)


def human_readable_size(size_bytes: int) -> str:
    # https://stackoverflow.com/a/14822210
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(floor(log(size_bytes, 1024)))
    p = pow(1024, i)
    s = round(size_bytes / p, 2)
    return f'{s} {size_name[i]}'


def human_readable_time(ms: Union[int, float]) -> Tuple[int, int, int]:
    m, s = divmod(ms / 1000, 60)
    h, m = divmod(m, 60)
    return floor(h), floor(m), floor(s)


def is_int(string: str) -> bool:
    try:
        int(string)
        return True
    except ValueError:
        return False


def machine_readable_time(colon_delimited_time: str) -> int:
    # Parse colon delimited time (e.g. "1:30:00") into milliseconds
    time_segments = colon_delimited_time.split(':')
    s = int(time_segments[-1])
    m = int(time_segments[-2])
    h = int(time_segments[0]) if len(time_segments) == 3 else 0
    return h * 3600000 + m * 60000 + s * 1000


def num_to_emoji(num: int, unicode: bool = False):
    suffix = '\U0000fe0f\U000020e3'
    if num == 1:
        return f'\U00000031{suffix}' if unicode else ':one:'
    elif num == 2:
        return f'\U00000032{suffix}' if unicode else ':two:'
    elif num == 3:
        return f'\U00000033{suffix}' if unicode else ':three:'
    elif num == 4:
        return f'\U00000034{suffix}' if unicode else ':four:'
    elif num == 5:
        return f'\U00000035{suffix}' if unicode else ':five:'
    return ""


def parse_spotify_url(url: str, valid_types: list[str] = ["track", "album", "artist", "playlist"]) -> tuple[str, str]:
    if not check_spotify_url(url):
        raise SpotifyInvalidURLError(url)

    parsed_path = []
    if re.match(r"^https?://open\.spotify\.com", url):
        # We are dealing with a link
        parsed_url = urlparse(url)
        parsed_path = parsed_url.path.split("/")[1:]
    elif re.match(r"^spotify:[a-z]", url):
        # We are dealing with a Spotify URI
        parsed_path = url.split(":")[1:]
    if len(parsed_path) < 2 or parsed_path[0] not in valid_types:
        raise SpotifyInvalidURLError(url)

    return parsed_path[0], parsed_path[1]


def reconstruct_url(rec_type: str, rec_id: str) -> str:
    if "spotify" in rec_type:
        # Spotify url
        split = rec_type.split('-')
        return 'https://open.spotify.com/{0}/{1}'.format(split[1], rec_id)
    elif rec_type == "youtube-video":
        return 'https://www.youtube.com/watch?v={}'.format(rec_id)
    return rec_id
