from nextcord.ext import commands
from nextcord import Embed
from math import floor, ceil
from itertools import islice
from DiscordUtils.Pagination import AutoEmbedPaginator
from spotipy.exceptions import SpotifyException
import asyncio
import re
from util import *


def dict_chunks(data):
    it = iter(data)
    for i in range(0, len(data), 5):
        yield {k: data[k] for k in islice(it, 5)}


async def remove_multiple_messages(ctx, ids):
    for msg_id in ids:
        try:
            msg = await ctx.fetch_message(int(msg_id))
            await msg.delete()
        except Exception as e:
            print("Error while trying to remove message: {}".format(e))


class Recommendation(commands.Cog):
    def __init__(self, client, db, spotify, youtube_api_key):
        self.client = client
        self.db = db
        self.spotify = spotify.get_client()
        self.spotify_rec = SpotifyRecommendation(self.spotify)
        self.youtube_rec = YouTubeRecommendation(youtube_api_key)

    def __add_recommendation(self, entity_id, rec, server=False):
        self.db.child("recommendations").child("server" if server else "user").child(str(entity_id)).push(rec)

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
        embed.set_thumbnail(url=ctx.guild.icon.url if server else ctx.author.avatar.url)
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
            reaction, _ = await self.client.wait_for("reaction_add", timeout=10.0, check=check)

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

    def __get_raw_recommendations(self, entity_id, server=False):
        return self.db.child("recommendations").child("server" if server else "user").child(str(entity_id))

    async def __get_recommendations(self, ctx, name, image, server=False, entity_id=""):
        # Get all recommendations for user/server
        entity = ctx.guild.id if server else entity_id
        rec_list = self.__get_raw_recommendations(entity, server=server).get().val()
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
                    desc = ""

                    if "author" in item:
                        desc += "by {}\n".format(item['author'])
                    if "id" in item:
                        desc += "{}\n".format(reconstruct_url(item['type'], item['id']))

                    desc += "{0}\nAdded by {1}".format(item['type'], item['recommender'])
                    field_name = "{0} - {1}".format(index, item['name'])
                    embed.add_field(name=field_name, value=desc, inline=False)
                    index += 1
                embeds.append(embed)

            await paginator.run(embeds)
        else:
            await ctx.reply("Recommendation list for {} is currently empty.".format(name))

    async def __remove_recommendation(self, ctx, index, server=False):
        # Check if user has recommendations and if requested index is in range
        entity_id = ctx.guild.id if server else ctx.author.id
        owner = "the server's" if server else "{}'s".format(ctx.author.mention)
        rec_list = self.__get_raw_recommendations(entity_id, server=server).get().val()

        if rec_list and len(rec_list):
            if len(rec_list) >= index:
                index = list(rec_list.keys())[index - 1]
                rec_name = rec_list[index]['name']
                recommender = "Added by {}".format(rec_list[index]['recommender'])

                if await self.__create_remove_dialog(ctx, server, rec_name, recommender):
                    self.__get_raw_recommendations(entity_id, server=server).child(index).remove()
                    await ctx.reply(":white_check_mark: Removed **'{0}'** from {1} list".format(rec_name, owner))

            else:
                await ctx.reply("Index {} is out of range.".format(index))
        else:
            await ctx.reply("Nothing found in {} list.".format(owner))

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
        description = "To recommend a result, type `rc!select {} <index>`."
        results = self.spotify.search(query, limit=5, type='artist,album,track')
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

    async def __add(self, ctx, mentions, rec):
        """Add recommendation to list. If uri is specified, recommendation details are pulled from Spotify."""
        if not len(mentions):
            recipient = "the server"
            self.__add_recommendation(ctx.guild.id, rec, server=True)
        else:
            recipients = []
            for user in mentions:
                recipients.append("<@{0}>".format(user))
                self.__add_recommendation(user, rec, server=False)
            recipient = ", ".join(recipients)

        success = ":white_check_mark: Recommended '**{0}**' to {1}".format(rec['name'], recipient)
        await ctx.reply(success)

    @commands.guild_only()
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
            mentions = [user.id for user in ctx.message.mentions]

            # Iterate through each argument, so we can add multiple tracks at once
            for arg in args:
                # Check that this argument isn't a @mention
                if not re.match(r"<((@[&!]?)|#)(\d+)>", arg):
                    # Check if we are dealing with a Spotify link
                    if check_spotify_url(arg):
                        try:
                            await self.__add(ctx, mentions, self.spotify_rec.parse(arg, ctx.author.name))
                        except SpotifyException:
                            await ctx.reply("Spotify link doesn't point to a valid Spotify item.")
                        except (SpotifyInvalidURLError, SpotifyNotFoundError) as e:
                            await ctx.reply(e)
                    # Check if we are dealing with a YouTube video link
                    elif self.youtube_rec.match(arg):
                        try:
                            await self.__add(ctx, mentions, self.youtube_rec.parse(arg, ctx.author.name))
                        except Exception as e:
                            await ctx.reply("Error processing YouTube link: {}".format(e))
                            await self.__add(ctx, mentions, {
                                "name": arg,
                                "recommender": ctx.author.name,
                                "type": "bookmark",
                            })
                    elif check_url(arg):
                        # Generic link
                        await self.__add(ctx, mentions, {
                            "name": arg,
                            "recommender": ctx.author.name,
                            "type": "bookmark",
                        })
                    else:
                        non_links.append(arg)

            # Process everything that isn't a link
            search_ctx = await self.__search(ctx, " ".join(non_links))
            self.__set_search_context(ctx.author, search_ctx)
        else:
            # Check for previous context
            prev_ctx = self.__get_search_context(ctx.author).val()
            if prev_ctx and "query" in prev_ctx and len(prev_ctx['query']):
                await self.__add(ctx, prev_ctx['mentions'] if "mentions" in prev_ctx else [], {
                    "name": prev_ctx['query'],
                    "recommender": ctx.author.name,
                    "type": "text",
                })
                await remove_multiple_messages(ctx, prev_ctx["embeds"])
            else:
                await ctx.reply("Please specify something to recommend.")

    @commands.guild_only()
    @commands.command(name='select', aliases=['recselect', 'recsel', 'rs'])
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
                    await self.__add(ctx, mentions, self.spotify_rec.parse(spotify_uri, ctx.author.name))
                    await remove_multiple_messages(ctx, prev_ctx["embeds"])
                    self.__clear_search_context(ctx.author)
                else:
                    await ctx.reply("Index {} is out of range.".format(index + 1))
            elif is_int(args[0]):
                await ctx.reply('\n'.join([
                    "Seems like you forgot to specify recommendation type!",
                    "Try again like this: `rc!{0} track {1}`".format(ctx.invoked_with, args[0])
                ]))
            else:
                await ctx.reply("Invalid search context, please try recommending again.")
                self.__clear_search_context(ctx.author)
        else:
            await ctx.reply("Incomplete command.")

    @commands.command(aliases=['l'])
    async def list(self, ctx):
        """
        List stuff recommended to you or other people.

        To see other people's lists, mention them after the command.
        e.g. rc!list @someone
        """
        if not len(ctx.message.mentions):
            await self.__get_recommendations(ctx, ctx.author.name, ctx.author.avatar.url, server=False, entity_id=str(ctx.author.id))
        else:
            user = ctx.message.mentions[0]
            await self.__get_recommendations(ctx, user.name, user.avatar.url, server=False, entity_id=str(user.id))

    @commands.guild_only()
    @commands.command(aliases=['ls'])
    async def listsvr(self, ctx):
        """List stuff recommended to everyone on the server."""
        await self.__get_recommendations(ctx, ctx.guild.name, ctx.guild.icon.url, server=True)

    @commands.command(aliases=['clr', 'c'])
    async def clear(self, ctx):
        """Clear your recommendations."""
        if await self.__create_remove_dialog(ctx, server=False):
            self.db.child("recommendations").child("user").child(str(ctx.author.id)).remove()
            await ctx.reply("Cleared your recommendations.")

    @commands.guild_only()
    @commands.command(aliases=['clrsvr', 'cs'])
    async def clearsvr(self, ctx):
        """
        Clear the server recommendations.
        Only a member with the Administrator permission can issue this command.
        """
        if ctx.author.guild_permissions.administrator:
            if await self.__create_remove_dialog(ctx, server=True):
                self.db.child("recommendations").child("server").child(str(ctx.guild.id)).remove()
                await ctx.reply("Cleared server recommendations.")
        else:
            await ctx.reply("Only administrators can clear server recommendations.")

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
            await ctx.reply("Invalid or missing index.")

    @commands.guild_only()
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
                await ctx.reply("Invalid or missing index.")
        else:
            await ctx.reply("Only administrators can remove server recommendations.")
