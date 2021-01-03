from discord.ext import commands
from discord import Embed
from math import floor, ceil
from itertools import islice
from DiscordUtils.Pagination import AutoEmbedPaginator
from spotipy.exceptions import SpotifyException
import asyncio
import re
from util import *


url_regex = r"(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"


def is_int(string):
    try:
        int(string)
        return True
    except ValueError:
        return False


def num_to_emoji(num: int):
    if num == 1:
        return ":one:"
    elif num == 2:
        return ":two:"
    elif num == 3:
        return ":three:"
    elif num == 4:
        return ":four:"
    elif num == 5:
        return ":five:"
    return ""


def dict_chunks(data):
    it = iter(data)
    for i in range(0, len(data), 5):
        yield {k: data[k] for k in islice(it, 5)}


class Recommendation(commands.Cog):
    def __init__(self, client, db, spotify, youtube_api_key):
        self.client = client
        self.db = db
        self.spotify = spotify
        self.spotify_rec = SpotifyRecommendation(spotify)
        self.youtube_rec = YouTubeRecommendation(youtube_api_key)

    def __add_recommendation(self, server_id, name, rec):
        self.db.child("recommendations").child(str(server_id)).child("server").push({
            "name": name,
            "link": rec
        })

    def __add_recommendation_user(self, server_id, user_id, name, rec):
        self.db.child("recommendations").child(str(server_id)).child(str(user_id)).push({
            "name": name,
            "link": rec
        })

    async def __create_remove_dialog(self, ctx, server=False, field_name=None, field_value=None):
        is_clearing = not field_name and not field_value
        title = "Really remove the following recommendation?"
        if is_clearing:
            owner = ctx.guild.name if server else ctx.author.name
            title = "Really remove all recommendations for {}?".format(owner)

        # Show dialog embed
        embed = Embed(title=title,
                      description="React :thumbsup: within the next 10 sec to confirm. This action is irreversible!",
                      color=0xff6600)
        embed.set_thumbnail(url=ctx.guild.icon_url if server else ctx.author.avatar_url)
        if not is_clearing:
            embed.add_field(name=field_name, value=field_value)
        dialog = await ctx.send(embed=embed)

        # Add reactions
        up = '\U0001f44d'
        down = '\U0001f44e'
        await dialog.add_reaction(up)
        await dialog.add_reaction(down)

        # Wait for user reaction
        try:
            def check(r, u):
                return str(r.emoji) in [up, down] and u == ctx.author
            reaction, user = await self.client.wait_for("reaction_add", timeout=10.0, check=check)

            if str(reaction.emoji) == up:
                await dialog.delete()
                return True
            elif str(reaction.emoji) == down:
                await dialog.delete()
                await ctx.send("{}: Got it, not removing.".format(ctx.author.mention))
        except asyncio.exceptions.TimeoutError:
            await dialog.remove_reaction(up, self.client.user)
            await dialog.remove_reaction(down, self.client.user)
            await ctx.send("{}: Timed out, not removing.".format(ctx.author.mention))
        return False

    def __get_raw_recommendations(self, guild_id, user_id):
        return self.db.child("recommendations").child(str(guild_id)).child(user_id)

    async def __get_recommendations(self, ctx, user_id, name, name_if_empty, image):
        # Get all recommendations for user/server
        rec_list = self.__get_raw_recommendations(ctx.guild.id, user_id).get().val()
        index = 1

        if rec_list and len(rec_list.keys()):
            # Create paginated embeds
            paginator = AutoEmbedPaginator(ctx)
            embeds = []
            embed_title = "Recommendations for {}".format(name)
            embed_desc = "{} items total".format(len(rec_list.keys()))

            for chunk in dict_chunks(rec_list):
                embed = Embed(title=embed_title, description=embed_desc, color=0x20ce09)
                embed.set_thumbnail(url=image)
                for key in chunk:
                    item = rec_list[key]
                    field_name = "{0} - {1}".format(index, item['name'])
                    embed.add_field(name=field_name, value=item['link'] or "No link available", inline=False)
                    index += 1
                embeds.append(embed)

            await paginator.run(embeds)
        else:
            await ctx.send("{} recommendation list is currently empty.".format(name_if_empty))

    async def __remove_recommendation(self, ctx, index, server=False):
        # Check if user has recommendations and if requested index is in range
        user_id = "server" if server else ctx.author.id
        owner = "the server's" if server else "{}'s".format(ctx.author.mention)
        rec_list = self.__get_raw_recommendations(ctx.guild.id, user_id).get().val()

        if rec_list and len(rec_list):
            if len(rec_list) >= index:
                index = list(rec_list.keys())[index - 1]
                rec_name = rec_list[index]['name']

                if await self.__create_remove_dialog(ctx, server, rec_name, rec_list[index]['link']):
                    self.__get_raw_recommendations(ctx.guild.id, user_id).child(index).remove()
                    await ctx.send(":white_check_mark: Removed **'{0}'** from {1} list".format(rec_name, owner))

            else:
                await ctx.send("{0}: Index {1} is out of range.".format(ctx.author.mention, index))
        else:
            await ctx.send("{0}: Nothing found in {1} list.".format(ctx.author.mention, owner))

    def __get_search_context(self, user):
        return self.db.child("contexts").child(str(user.id)).get()

    def __set_search_context(self, user, ctx):
        self.db.child("contexts").child(str(user.id)).set(ctx)

    def __clear_search_context(self, user):
        self.db.child("contexts").child(str(user.id)).remove()

    async def __search(self, ctx, query):
        if not len(query):
            return

        # Search for matches in Spotify
        title = "Top 5 matching Spotify {0}s for '{1}'"
        description = "To recommend a result, type `rc!recselect {} <index>`."
        results = self.spotify.search(query, limit=5, type='artist,album,track')
        context = {
            "mentions": [{"id": user.id, "name": user.name} for user in ctx.message.mentions],
            "query": query,
            "track": [],
            "album": [],
            "artist": []
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
            await ctx.send(embed=embed)
        else:
            await ctx.send("No tracks matching '{}' found on Spotify.".format(query))

        # Show matching albums
        if len(results['albums']['items']):
            embed = Embed(title=title.format("album", query), description=description.format("album"), color=0x20ce09)
            for item in enumerate(results['albums']['items']):
                field_name = "{0} {1}".format(num_to_emoji(item[0] + 1), item[1]['name'])
                field_value = "{0}, {1}".format(item[1]['artists'][0]['name'], item[1]['release_date'])
                embed.add_field(name=field_name, value=field_value, inline=False)
                context["album"].append(item[1]['id'])
            await ctx.send(embed=embed)
        else:
            await ctx.send("No albums matching '{}' found on Spotify.".format(query))

        # Show matching artists
        if len(results['artists']['items']):
            embed = Embed(title=title.format("artist", query), description=description.format("artist"), color=0x20ce09)
            for item in enumerate(results['artists']['items']):
                field_name = "{0} - {1}".format(num_to_emoji(item[0] + 1), item[1]['name'])
                field_value = "{} followers".format(item[1]['followers']['total'])
                embed.add_field(name=field_name, value=field_value, inline=False)
                context["artist"].append(item[1]['id'])
            await ctx.send(embed=embed)
        else:
            await ctx.send("No artists matching '{}' found on Spotify.".format(query))

        # Save context for later
        await ctx.send("{0}: To recommend '{1}' as is, type only `rc!rec`.".format(ctx.author.mention, query))
        return context

    async def __add(self, ctx, mentions, name, description=""):
        """Add recommendation to list. If uri is specified, recommendation details are pulled from Spotify."""
        if not len(description):
            description = "Added by {}".format(ctx.author.name)

        if not len(mentions):
            recipient = "the server"
            self.__add_recommendation(ctx.guild.id, name, description)
        else:
            recipients = []
            for user in mentions:
                recipients.append(user['name'])
                self.__add_recommendation_user(ctx.guild.id, user['id'], name, description)
            recipient = ", ".join(recipients)

        success = ":white_check_mark: {0} recommended '**{1}**' to {2}".format(ctx.author.mention, name, recipient)
        await ctx.send(success)

    @commands.command(aliases=['r', 'add', 'rec'])
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
            mentions = [{"id": user.id, "name": user.name} for user in ctx.message.mentions]

            # Iterate through each argument, so we can add multiple tracks at once
            for arg in args:
                # Check that this argument isn't a @mention
                if not re.match(r"<((@[&!]?)|#)(\d+)>", arg):
                    # Check if we are dealing with a Spotify link
                    if self.spotify_rec.match(arg):
                        try:
                            name, desc = self.spotify_rec.parse(arg, ctx.author.name)
                            await self.__add(ctx, mentions, name, desc)
                        except SpotifyException:
                            err = "{}: Spotify link detected, but it doesn't point to a valid Spotify item.".format(
                                ctx.author.mention
                            )
                            await ctx.send(err)
                        except (SpotifyInvalidURLError, SpotifyNotFoundError) as e:
                            await ctx.send("{0}: {1}".format(ctx.author.mention, e))
                    elif self.youtube_rec.match(arg):
                        try:
                            name, desc = self.youtube_rec.parse(arg, ctx.author.name)
                            await self.__add(ctx, mentions, name, desc)
                        except Exception as e:
                            await ctx.send("{0}: Error processing YouTube link. {1}".format(ctx.author.mention, e))
                    elif re.match(url_regex, arg):
                        # Generic link
                        await self.__add(ctx, mentions, "Bookmark by {}".format(ctx.author.name), arg)
                    else:
                        non_links.append(arg)

            # Process everything that isn't a link
            search_ctx = await self.__search(ctx, " ".join(non_links))
            self.__set_search_context(ctx.author, search_ctx)
        else:
            # Check for previous context
            prev_ctx = self.__get_search_context(ctx.author).val()
            if prev_ctx and "query" in prev_ctx and len(prev_ctx['query']):
                await self.__add(ctx, prev_ctx['mentions'] if "mentions" in prev_ctx else [], name=prev_ctx['query'])
            else:
                await ctx.send("{}, please specify something to recommend.".format(ctx.author.mention))

    @commands.command(aliases=['recsel', 'rs'])
    async def recselect(self, ctx, *args):
        """Select which item to recommend from results given by rc!recommend."""
        if len(args):
            prev_ctx = self.__get_search_context(ctx.author).val()
            if prev_ctx and args[0] in prev_ctx:
                items = prev_ctx[args[0]]
                index = int(args[1]) - 1

                if index in range(0, len(items)):
                    item = items[index]
                    mentions = prev_ctx['mentions'] if "mentions" in prev_ctx else []
                    spotify_uri = "spotify:{0}:{1}".format(args[0], item)
                    name, desc = self.spotify_rec.parse(spotify_uri, ctx.author.name)
                    await self.__add(ctx, mentions, name, desc)
                else:
                    await ctx.send("{0}: Index {1} is out of range.".format(ctx.author.mention, index + 1))
            elif is_int(args[0]):
                msg = "{0}: Seems like you forgot to specify recommendation type! ".format(ctx.author.mention)
                msg += "Try again like this: `rc!{0} track {1}`".format(ctx.command.name, args[0])
                await ctx.send(msg)
            else:
                await ctx.send("{}: Invalid search context, please try recommending again.".format(ctx.author.mention))
        else:
            await ctx.send("{}: Incomplete command.".format(ctx.author.mention))
        self.__clear_search_context(ctx.author)

    @commands.command(aliases=['l'])
    async def list(self, ctx):
        """
        List stuff recommended to you or other people.

        To see other people's lists, mention them after the command.
        e.g. rc!list @someone
        """
        if not len(ctx.message.mentions):
            await self.__get_recommendations(ctx, str(ctx.author.id), ctx.author.name, "Your", ctx.author.avatar_url)
        else:
            user = ctx.message.mentions[0]
            await self.__get_recommendations(ctx, str(user.id), user.name, "{}'s".format(user.name), user.avatar_url)

    @commands.command(aliases=['ls'])
    async def listsvr(self, ctx):
        """List stuff recommended to everyone on the server."""
        await self.__get_recommendations(ctx, "server", ctx.guild.name, "This server's", ctx.guild.icon_url)

    @commands.command(aliases=['clr', 'c'])
    async def clear(self, ctx):
        """Clear your recommendations."""
        if await self.__create_remove_dialog(ctx, server=False):
            self.db.child("recommendations").child(str(ctx.guild.id)).child(str(ctx.author.id)).remove()
            await ctx.send("{}: Cleared your recommendations.".format(ctx.author.mention))

    @commands.command(aliases=['clrsvr', 'cs'])
    async def clearsvr(self, ctx):
        """
        Clear the server recommendations.
        Only a member with the Administrator permission can issue this command.
        """
        if ctx.author.guild_permissions.administrator:
            if await self.__create_remove_dialog(ctx, server=True):
                self.db.child("recommendations").child(str(ctx.guild.id)).child("server").remove()
                await ctx.send("{}: Cleared server recommendations.".format(ctx.author.mention))
        else:
            await ctx.send("{}, only administrators can clear server recommendations.".format(ctx.author.mention))

    @commands.command(aliases=['rm', 'del'])
    async def remove(self, ctx, *args):
        """
        Remove a recommendation from your list.
        To use, type rc!remove <index>, where <index> is the number of the recommendation
        you wish to remove, as listed by rc!list.
        """
        if len(args) and is_int(args[0]):
            await self.__remove_recommendation(ctx, int(args[0]))
        else:
            await ctx.send("{}: Invalid or missing index.".format(ctx.author.mention))

    @commands.command(aliases=['rms', 'dels'])
    async def removesvr(self, ctx, *args):
        """
        Remove a recommendation from the server's list.
        To use, type rc!remove <index>, where <index> is the number of the recommendation
        you wish to remove, as listed by rc!listsvr.
        """
        if ctx.author.guild_permissions.administrator:
            if len(args) and is_int(args[0]):
                await self.__remove_recommendation(ctx, int(args[0]), server=True)
            else:
                await ctx.send("{}: Invalid or missing index.".format(ctx.author.mention))
        else:
            await ctx.send("{}, only administrators can remove server recommendations.".format(ctx.author.mention))
