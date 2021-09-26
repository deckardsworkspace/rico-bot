from math import floor, ceil
from nextcord import Embed
from nextcord.ext.commands import Context
from pyrebase.pyrebase import Database
from spotipy import Spotify
from typing import Dict, List
from util import num_to_emoji, remove_multiple_messages, SpotifyRecommendation
from .recommend_db import add
from .search_context import clear_search_context, get_search_context


async def create_match_reacts(ctx: Context, db: Database, spotify_rec: SpotifyRecommendation, messages: List[int],
                              results: Dict):
    num_reacts = [num_to_emoji(i, unicode=True) for i in range(1, 6)]
    match_types = ['track', 'artist', 'album']

    # Add reactions
    for i in zip(range(len(match_types)), match_types):
        match_type_i, match_type = i
        message = await ctx.fetch_message(messages[match_type_i])
        match_num = len(results[f'{match_type}s']['items'])

        for j in range(1, match_num + 1):
            react = num_to_emoji(j, unicode=True)
            num_reacts.append(react)
            await message.add_reaction(react)

    # Wait for user reaction
    try:
        def check(r, u):
            return str(r.emoji) in num_reacts and u == ctx.author
        reaction, _ = await ctx.bot.wait_for("reaction_add", timeout=30.0, check=check)

        match_type = messages.index(reaction.message.id)
        await handle_match(ctx, db, spotify_rec, match_types[match_type], num_reacts.index(reaction.emoji))
    except TimeoutError:
        await ctx.reply('Took too long selecting a match, aborting.')
        clear_search_context(db, ctx.author)


async def handle_match(ctx: Context, db: Database, spotify_rec: SpotifyRecommendation,
                       match_type: str, index: int):
    """Select which item to recommend from results given by rc!recommend."""
    prev_ctx = get_search_context(db, ctx.author).val()

    if prev_ctx:
        items = prev_ctx[match_type]

        if index in range(len(items)):
            item = items[index]
            mentions = prev_ctx['mentions'] if "mentions" in prev_ctx else []
            spotify_uri = "spotify:{0}:{1}".format(match_type, item)
            await add(ctx, db, mentions, spotify_rec.parse(spotify_uri, ctx.author.name))
            await remove_multiple_messages(ctx, prev_ctx["embeds"])
            clear_search_context(db, ctx.author)
        else:
            await ctx.reply("Index {} is out of range.".format(index + 1))
    else:
        await ctx.reply("Invalid search context, please try recommending again.")
        clear_search_context(db, ctx.author)


async def search(db: Database, spotify: Spotify, spotify_rec: SpotifyRecommendation, ctx: Context, query: str):
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

    # Save context for later
    msg = await ctx.reply("To recommend '{}' as text, type `rc!rec`.".format(query))
    context["embeds"].append(msg.id)

    # Add selection emojis
    await create_match_reacts(ctx, db, spotify_rec, context['embeds'], results)
    return context
