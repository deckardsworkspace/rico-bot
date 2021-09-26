from nextcord.ext.commands import command, guild_only
from spotipy.exceptions import SpotifyException
from util import check_spotify_url, check_url, remove_multiple_messages
from util import SpotifyInvalidURLError, SpotifyNotFoundError
from .recommend_db import add
from .search import search
from .search_context import get_search_context, set_search_context
import re


@guild_only()
@command(aliases=['r', 'add', 'rec'])
async def recommend(self, ctx, *args):
    """
    Recommend something to someone or the server.
    Supports Spotify links, or if a link isn't found, will search for matches on Spotify.

    To recommend something to a specific person, @mention them after the command,
    e.g. rc!rec @person sugar brockhampton.

    To recommend something to the server, no need to @mention anyone, just type the recommendation.
    e.g. rc!rec HONNE
    """
    if len(args):
        non_links = []
        mentions = [user.id for user in ctx.message.mentions]

        # Iterate through each argument, so we can add multiple tracks at once
        for arg in args:
            # Check that this argument isn't a @mention
            if not re.match(r"<((@[&!]?)|#)(\d+)>", arg):
                # Check if we are dealing with a Spotify link
                if check_spotify_url(arg):
                    try:
                        await add(ctx, self.db, mentions, self.spotify_rec.parse(arg, ctx.author.name))
                    except SpotifyException:
                        await ctx.reply("Spotify link doesn't point to a valid Spotify item.")
                    except (SpotifyInvalidURLError, SpotifyNotFoundError) as e:
                        await ctx.reply(e)
                # Check if we are dealing with a YouTube video link
                elif self.youtube_rec.match(arg):
                    try:
                        await add(ctx, self.db, mentions, self.youtube_rec.parse(arg, ctx.author.name))
                    except Exception as e:
                        await ctx.reply("Error processing YouTube link: {}".format(e))
                        await add(ctx, self.db, mentions, {
                            "name": arg,
                            "recommender": ctx.author.name,
                            "type": "bookmark",
                        })
                elif check_url(arg):
                    # Generic link
                    await add(ctx, self.db, mentions, {
                        "name": arg,
                        "recommender": ctx.author.name,
                        "type": "bookmark",
                    })
                else:
                    non_links.append(arg)

        # Process everything that isn't a link
        search_ctx = await search(self.db, self.spotify, self.spotify_rec, ctx, " ".join(non_links))
        set_search_context(self.db, ctx.author, search_ctx)
    else:
        # Check for previous context
        prev_ctx = get_search_context(self.db, ctx.author).val()
        if prev_ctx and "query" in prev_ctx and len(prev_ctx['query']):
            await add(ctx, self.db, prev_ctx['mentions'] if "mentions" in prev_ctx else [], {
                "name": prev_ctx['query'],
                "recommender": ctx.author.name,
                "type": "text",
            })
            await remove_multiple_messages(ctx, prev_ctx["embeds"])
        else:
            await ctx.reply("Please specify something to recommend.")
