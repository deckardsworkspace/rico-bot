from asyncio.exceptions import TimeoutError
from dataclasses import asdict
from math import floor, ceil
from nextcord import Embed
from nextcord.ext.commands import Context
from pyrebase.pyrebase import Database
from spotipy import Spotify
from typing import Dict
from util import get_var, num_to_emoji, remove_multiple_messages, SpotifyRecommendation
from util.recommendation import rec_factory
from .recommend_db import add


async def create_match_reacts(ctx: Context, db: Database, spotify: Spotify, search_ctx: Dict):
    num_reacts = [num_to_emoji(i, unicode=True) for i in range(1, 6)]
    match_types = ['track', 'album', 'artist']
    messages = search_ctx['embeds']

    # Add reactions
    for i in zip(range(len(match_types)), match_types):
        match_type_i, match_type = i
        message = await ctx.fetch_message(messages[match_type_i])
        match_num = len(search_ctx[match_type])

        for j in range(match_num):
            await message.add_reaction(num_reacts[j])

    # Wait for user reaction
    try:
        def check(r, u):
            return str(r.emoji) in num_reacts and u == ctx.author and r.message.id == message.id
        reaction, _ = await ctx.bot.wait_for("reaction_add", timeout=30.0, check=check)

        match_type = match_types[messages.index(reaction.message.id)]
        match_index = num_reacts.index(reaction.emoji)
        match_id = search_ctx[match_type][match_index]
        await handle_match(ctx, db, spotify, match_type, match_id)
    except TimeoutError:
        await ctx.reply('Took too long selecting a match, aborting.')
    finally:
        # Delete messages
        await remove_multiple_messages(ctx, messages)


async def handle_match(ctx: Context, db: Database, spotify: Spotify, match_type: str, match_id: str):
    """Select which item to recommend from results given by rc!recommend."""
    spotify_uri = "spotify:{0}:{1}".format(match_type, match_id)
    mentions = [user.id for user in ctx.message.mentions]
    rec = SpotifyRecommendation(url=spotify_uri, recommender=ctx.author.name, spotify=spotify)
    await add(ctx, db, mentions, asdict(rec, dict_factory=rec_factory))


async def search(db: Database, spotify: Spotify, ctx: Context, query: str):
    if not len(query):
        return

    # Search for matches in Spotify
    title = "Top 5 matching Spotify {0}s for '{1}'"
    description = "To recommend a result, react with the appropriate emoji."
    results = spotify.search(query, limit=5, type='artist,album,track')
    context = {
        "mentions": [user.id for user in ctx.message.mentions],
        "query": query,
        "track": [],
        "album": [],
        "artist": [],
        "embeds": []
    }

    # Show matching tracks
    if len(results['tracks']['items']):
        embed = Embed(title=title.format("track", query), description=description.format("track"), color=0x20ce09)
        for item in enumerate(results['tracks']['items']):
            ms = item[1]['duration_ms']
            duration_sec = ceil((ms / 1000) % 60) if ms > 10000 else "0{}".format(ceil((ms / 1000) % 60))
            duration = "{0}m {1}s".format(floor((ms / (1000 * 60)) % 60), duration_sec)
            field_name = "{0} {1} ({2})".format(num_to_emoji(item[0] + 1), item[1]['name'], duration)
            field_value = item[1]['artists'][0]['name']
            embed.add_field(name=field_name, value=field_value, inline=False)
            context["track"].append(item[1]['id'])

        sent_embed = await ctx.send(embed=embed)
        context["embeds"].append(sent_embed.id)
    else:
        context["embeds"].append((await ctx.send("No tracks matching '{}' found on Spotify.".format(query))).id)

    # Show matching albums
    if len(results['albums']['items']):
        embed = Embed(title=title.format("album", query), description=description.format("album"), color=0x20ce09)
        for item in enumerate(results['albums']['items']):
            field_name = "{0} {1}".format(num_to_emoji(item[0] + 1), item[1]['name'])
            field_value = "{0}, {1}".format(item[1]['artists'][0]['name'], item[1]['release_date'])
            embed.add_field(name=field_name, value=field_value, inline=False)
            context["album"].append(item[1]['id'])

        sent_embed = await ctx.send(embed=embed)
        context["embeds"].append(sent_embed.id)
    else:
        context["embeds"].append((await ctx.send("No albums matching '{}' found on Spotify.".format(query))).id)

    # Show matching artists
    if len(results['artists']['items']):
        embed = Embed(title=title.format("artist", query), description=description.format("artist"), color=0x20ce09)
        for item in enumerate(results['artists']['items']):
            field_name = "{0} - {1}".format(num_to_emoji(item[0] + 1), item[1]['name'])
            field_value = "{} followers".format(item[1]['followers']['total'])
            embed.add_field(name=field_name, value=field_value, inline=False)
            context["artist"].append(item[1]['id'])

        sent_embed = await ctx.send(embed=embed)
        context["embeds"].append(sent_embed.id)
    else:
        context["embeds"].append((await ctx.send("No artists matching '{}' found on Spotify.".format(query))).id)

    # Add selection emojis
    msg = await ctx.reply("To recommend '{0}' as text, please use `{1}rt {2}`.".format(
        query, get_var('BOT_PREFIX'), query
    ))
    context["embeds"].append(msg.id)
    await create_match_reacts(ctx, db, spotify, context)
