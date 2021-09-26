from nextcord.ext import commands
from util import SpotifyRecommendation, YouTubeRecommendation


class Recommendation(commands.Cog):
    def __init__(self, client, db, spotify, youtube_api_key):
        self.client = client
        self.db = db
        self.spotify = spotify.get_client()
        self.spotify_rec = SpotifyRecommendation(self.spotify)
        self.youtube_rec = YouTubeRecommendation(youtube_api_key)

    # Commands
    from .cmd_clear import clear, clear_guild, remove, remove_guild
    from .cmd_list import list_guild, list_personal
    from .cmd_recommend import recommend, recselect
