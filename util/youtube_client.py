from dataclasses import dataclass
from typing import List
from youtubesearchpython import VideosSearch
from .string_util import machine_readable_time


@dataclass
class YouTubeResult:
    title: str
    author: str
    duration_ms: int
    url: str


def get_youtube_matches(query: str, desired_duration_ms: int = 0, num_results: int = 10) -> List[YouTubeResult]:
    results = []

    search = VideosSearch(query, limit=num_results)
    search_results = search.result()
    if 'result' in search_results.keys():
        for result in search_results['result']:
            duration = machine_readable_time(result['duration']) if result['duration'] is not None else 0
            results.append(YouTubeResult(
                title=result['title'],
                author=result['channel']['name'],
                duration_ms=duration,
                url=result['link']
            ))
    
    if desired_duration_ms > 0:
        # Sort results by distance to desired duration
        results.sort(key=lambda x: abs(x.duration_ms - desired_duration_ms))
    return results
