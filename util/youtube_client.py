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
    duration = machine_readable_time(result['duration']) if result['duration'] is not None else 0
    return YouTubeResult(
        title=result['title'],
        author=result['channel']['name'],
        duration_ms=duration,
        url=result['link']
    )


def get_youtube_playlist_info(playlist_id: str) -> Tuple[str, str, int]:
    playlist_info = Playlist.getInfo(playlist_id)
    return playlist_info['title'], playlist_info['channel']['name'], int(playlist_info['videoCount'])


def get_youtube_playlist_tracks(playlist_id: str) -> Tuple[List[YouTubeResult]]:
    playlist = Playlist(playlist_id)
    tracks = [parse_result(i) for i in playlist.videos]
    while playlist.hasMoreVideos:
        playlist.getNextVideos()
        tracks.extend([parse_result(i) for i in playlist.videos])
    return tracks


def get_youtube_video(video_id: str) -> YouTubeResult:
    video = Video.get(video_id)
    return parse_result(video)


def get_youtube_matches(query: str, desired_duration_ms: int = 0, num_results: int = 10) -> List[YouTubeResult]:
    results = []

    search = VideosSearch(query, limit=num_results)
    search_results = search.result()
    if 'result' in search_results.keys():
        for result in search_results['result']:
            if result['duration'] is None:
                # Can't play a track with no duration
                continue
            results.append(parse_result(result))
    
    if desired_duration_ms > 0:
        # Sort results by distance to desired duration
        results.sort(key=lambda x: abs(x.duration_ms - desired_duration_ms))
    return results
