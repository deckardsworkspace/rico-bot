from dataclasses import asdict
from nextcord.ext.commands import command, Context, guild_only
from spotipy.exceptions import SpotifyException
from util import (
    check_spotify_url, check_url, check_youtube_url,
    SpotifyInvalidURLError, SpotifyNotFoundError,
    SpotifyRecommendation, YouTubeRecommendation
)
from util.recommendation import rec_factory
from .recommend_db import add
from .search import search
import re


@guild_only()
@command(aliases=['r', 'add', 'rec'])
async def recommend(self, ctx, *args):
    """
    Recommend something on Spotify to someone or the server.

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
                        rec = SpotifyRecommendation(arg, ctx.author.name)
                        await add(ctx, self.db, mentions, asdict(rec, dict_factory=rec_factory))
                    except SpotifyException:
                        await ctx.reply("Spotify link doesn't point to a valid Spotify item.")
                    except (SpotifyInvalidURLError, SpotifyNotFoundError) as e:
                        await ctx.reply(e)
                # Check if we are dealing with a YouTube video link
                elif check_youtube_url(arg):
                    try:
                        rec = YouTubeRecommendation(arg, ctx.author.name)
                        await add(ctx, self.db, mentions, asdict(rec, dict_factory=rec_factory))
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
                        "recommender": ctx.author.id,
                        "type": "bookmark",
                    })
                else:
                    non_links.append(arg)

        # Process everything that isn't a link
        await search(self.db, self.spotify, ctx, " ".join(non_links))
    else:
        await ctx.reply("Please specify something to recommend.")


@command(name='rectext', aliases=['rt'])
async def recommend_text(self, ctx: Context, *args):
    # Check for previous context
    if len(args):
        mentions = [user.id for user in ctx.message.mentions]
        rec_name = [arg for arg in args if not re.match(r"<((@[&!]?)|#)(\d+)>", arg)]
        await add(ctx, self.db, mentions, {
            "name": ' '.join(rec_name),
            "recommender": ctx.author.id,
            "type": "text"
        })
    else:
        await ctx.reply("Please specify something to recommend.")
