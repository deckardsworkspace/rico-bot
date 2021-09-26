from math import floor, ceil
from nextcord import Embed
from nextcord.ext.commands import Context
from spotipy import Spotify
from util import num_to_emoji


async def search(spotify: Spotify, ctx: Context, query: str):
    if not len(query):
        return

    # Search for matches in Spotify
    title = "Top 5 matching Spotify {0}s for '{1}'"
    description = "To recommend a result, type `rc!select {} <index>`."
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
        context["embeds"].append((await ctx.send(embed=embed)).id)
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
        context["embeds"].append((await ctx.send(embed=embed)).id)
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
        context["embeds"].append((await ctx.send(embed=embed)).id)
    else:
        context["embeds"].append((await ctx.send("No artists matching '{}' found on Spotify.".format(query))).id)

    # Save context for later
    msg = await ctx.reply("To recommend '{}' as text, type `rc!rec`.".format(query))
    context["embeds"].append(msg.id)
    return context
