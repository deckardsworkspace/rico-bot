def ellipsis_truncate(string):
    if len(string) < 200:
        return string
    return string[:196] + "..."


def reconstruct_url(rec_type: str, rec_id: str):
    if "spotify" in rec_type:
        # Spotify url
        split = rec_type.split('-')
        return 'https://open.spotify.com/{0}/{1}'.format(split[1], rec_id)
    elif rec_type == "youtube-video":
        return 'https://youtube.com/watch/{}'.format(rec_id)
    return rec_id
