from dataclasses import dataclass
from typing import Dict, List, Tuple
from youtubesearchpython import Playlist, Video, VideosSearch
from .string_util import machine_readable_time


@dataclass
class YouTubeResult:
    title: str
    author: str
    duration_ms: int
    url: str


def parse_result(result: Dict) -> YouTubeResult:
    duration = 0
    if 'duration' in result.keys() and result['duration'] is not None:
        duration = machine_readable_time(result['duration'])
    return YouTubeResult(
        title=result['title'],
        author=result['channel']['name'],
        duration_ms=duration,
        url=f'https://www.youtube.com/watch?v={result["id"]}'
    )


def get_youtube_playlist_info(playlist_id: str) -> Tuple[str, str, int]:
    playlist_info = Playlist.getInfo(f'http://youtube.com/playlist?list={playlist_id}')
    return playlist_info['title'], playlist_info['channel']['name'], int(playlist_info['videoCount'])


def get_youtube_playlist_tracks(playlist_id: str) -> Tuple[List[YouTubeResult]]:
    playlist = Playlist(f'http://youtube.com/playlist?list={playlist_id}')
    while playlist.hasMoreVideos:
        playlist.getNextVideos()
    return [parse_result(i) for i in playlist.videos]


def get_youtube_video(video_id: str) -> YouTubeResult:
    video = Video.get(video_id)
    return parse_result(video)


def get_youtube_matches(query: str, desired_duration_ms: int = 0, num_results: int = 10) -> List[YouTubeResult]:
    results = []

    search = VideosSearch(query, limit=num_results)
    search_results = search.result()
    if 'result' in search_results.keys():
        for result in search_results['result']:
            if 'duration' not in result.keys() or result['duration'] is None:
                # Can't play a track with no duration
                continue
            results.append(parse_result(result))
    
    if desired_duration_ms > 0:
        # Sort results by distance to desired duration
        results.sort(key=lambda x: abs(x.duration_ms - desired_duration_ms))
    return results
