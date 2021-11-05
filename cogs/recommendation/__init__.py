from nextcord.ext.commands import Cog


class Recommendation(Cog):
    def __init__(self, client, db, spotify):
        self.client = client
        self.db = db
        self.spotify = spotify.get_client()
        print('Loaded cog: Recommendation')

    # Commands
    from .cmd_clear import clear, clear_guild, remove, remove_guild
    from .cmd_list import list_guild, list_personal
    from .cmd_recommend import recommend, recommend_text
