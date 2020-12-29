from discord.ext import commands
from discord import Embed
from math import floor, ceil
from itertools import islice
from DiscordUtils.Pagination import AutoEmbedPaginator
import re


class Recommendation(commands.Cog):
    def __init__(self, client, db, spotify):
        self.client = client
        self.db = db
        self.spotify = spotify


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


    async def __get_recommendations(self, ctx, id, name, name_if_empty, image):
        # Get all recommendations for user/server
        rec_list = self.db.child("recommendations").child(str(ctx.guild.id)).child(id).get().val()

        if rec_list and len(rec_list.keys()):
            # Create paginated embeds
            paginator = AutoEmbedPaginator(ctx)
            embeds = []
            embed_title = "Recommendations for {}".format(name)
            embed_desc = "{} items total".format(len(rec_list.keys()))

            for chunk in self.__dict_chunks(rec_list):
                embed = Embed(title=embed_title, description=embed_desc, color=0x20ce09)
                embed.set_thumbnail(url=image)
                for key in chunk:
                    item = rec_list[key]
                    embed.add_field(name=item['name'], value=item['link'] or "No link available", inline=False)
                embeds.append(embed)

            await paginator.run(embeds)
        else:
            await ctx.message.reply("{} recommendation list is currently empty.".format(name_if_empty))


    def __get_search_context(self, user):
        return self.db.child("contexts").child(str(user.id)).get()


    def __set_search_context(self, user, ctx):
        self.db.child("contexts").child(str(user.id)).set(ctx)


    def __clear_search_context(self, user):
        self.db.child("contexts").child(str(user.id)).remove()


    def __num_to_emoji(self, num: int):
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


    def __dict_chunks(self, data):
        it = iter(data)
        for i in range(0, len(data), 10):
            yield {k:data[k] for k in islice(it, 10)}


    async def __search(self, ctx, query):
        # Search for matches in Spotify
        title = "Top 5 matching {0}s for '{1}'"
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
        embed = Embed(title=title.format("track", query), description=description.format("track"), color=0x20ce09)
        for item in enumerate(results['tracks']['items']):
            ms = item[1]['duration_ms']
            duration_sec = ceil((ms/1000)%60) if ms > 10000 else "0{}".format(ceil((ms/1000)%60))
            duration = "{0}:{1}".format(floor((ms/(1000*60))%60), duration_sec)
            field_name = "{0} {1} ({2})".format(self.__num_to_emoji(item[0] + 1), item[1]['name'], duration)
            field_value = item[1]['artists'][0]['name']
            embed.add_field(name=field_name, value=field_value, inline=False)
            context["track"].append(item[1]['id'])
        await ctx.send(embed=embed)

        # Show matching albums
        embed = Embed(title=title.format("album", query), description=description.format("album"), color=0x20ce09)
        for item in enumerate(results['albums']['items']):
            field_name = "{0} {1}".format(self.__num_to_emoji(item[0] + 1), item[1]['name'])
            field_value = "{0}, {1}".format(item[1]['artists'][0]['name'], item[1]['release_date'])
            embed.add_field(name=field_name, value=field_value, inline=False)
            context["album"].append(item[1]['id'])
        await ctx.send(embed=embed)

        # Show matching artists
        embed = Embed(title=title.format("artist", query), description=description.format("artist"), color=0x20ce09)
        for item in enumerate(results['artists']['items']):
            field_name = "{0} - {1}".format(self.__num_to_emoji(item[0] + 1), item[1]['name'])
            field_value = "{} followers".format(item[1]['followers']['total'])
            embed.add_field(name=field_name, value=field_value, inline=False)
            context["artist"].append(item[1]['id'])
        await ctx.send(embed=embed)

        # Save context for later
        await ctx.message.reply("{0}: To recommend '{1}' as is, type only `rc!rec`.".format(ctx.author.mention, query))
        return context


    async def __add(self, ctx, mentions, uri=None, name=""):
        """Add recommendation to list. If uri is specified, recommendation details are pulled from Spotify."""
        if uri is not None:
            if uri['type'] == 'album':
                result = self.spotify.album(uri['id'])
            elif uri['type'] == 'artist':
                result = self.spotify.artist(uri['id'])
            elif uri['type'] == 'track':
                result = self.spotify.track(uri['id'])
            elif uri['type'] == 'playlist':
                result = self.spotify.playlist(uri['id'])
            if not result:
                await ctx.send("Invalid Spotify identifier {}".format(uri['id']))
                return

            # Add to recommendation recipients
            name = "Spotify {}: {}".format(uri['type'], result['name'])
            link = "Recommended by {0} - https://open.spotify.com/{1}/{2}".format(ctx.author.name, uri['type'], uri['id'])
        else:
            link = "Recommended by {}".format(ctx.author.name)

        if not len(mentions):
            recipient = "the server"
            self.__add_recommendation(ctx.guild.id, name, link)
        else:
            recipients = []
            for user in mentions:
                recipients.append(user['name'])
                self.__add_recommendation_user(ctx.guild.id, user['id'], name, link)
            recipient = ", ".join(recipients)

        success = ":white_check_mark: {0} recommended '**{1}**' to {2}".format(ctx.author.mention, name, recipient)
        await ctx.message.reply(success)


    @commands.command(aliases=['r', 'add', 'rec'])
    async def recommend(self, ctx, *args):
        """
        Recommend something. Supports Spotify links.
        To recommend something to a specific person, mention them after the command,
        e.g. rc!rec @person sugar brockhampton.
        """
        if len(args):
            query = ' '.join(filter(lambda arg: not re.match(r"<((@(&|!)?)|#)(\d+)>", arg), args))

            # Check if we are dealing with a Spotify link
            if re.match(r"https?:\/\/open\.spotify\.com\/(track|artist|album|playlist)\/[a-zA-Z0-9]+", query):
                # Strip link down to Spotify URI format
                clean_query = re.sub(r"\?[a-zA-Z0-9]+=.*$", "", query)
                clean_query = re.sub(r"https?:\/\/open\.spotify\.com\/", "", clean_query)
                clean_query = re.sub(r"\/", ":", clean_query)
                split_query = clean_query.split(":")
                mentions = [{"id": user.id, "name": user.name} for user in ctx.message.mentions]
                await self.__add(ctx, mentions, uri={
                    'type': split_query[0],
                    'id': split_query[1]
                })
            else:
                search_ctx = await self.__search(ctx, query)
                self.__set_search_context(ctx.author, search_ctx)
        else:
            # Check for previous context
            prev_ctx = self.__get_search_context(ctx.author).val()
            if prev_ctx and "query" in prev_ctx and len(prev_ctx['query']):
                await self.__add(ctx, prev_ctx['mentions'] if "mentions" in prev_ctx else [], name=prev_ctx['query'])
            else:
                await ctx.message.reply("{}, please specify something to recommend.".format(ctx.author.mention))


    @commands.command(aliases=['recsel', 'rs'])
    async def recselect(self, ctx, *args):
        """Select which item to recommend from results given by rc!rec."""
        if len(args):
            prev_ctx = self.__get_search_context(ctx.author).val()
            if prev_ctx and args[0] in prev_ctx:
                items = prev_ctx[args[0]]
                index = int(args[1]) - 1

                if index in range(0, len(items)):
                    item = items[index]
                    await self.__add(ctx, prev_ctx['mentions'] if "mentions" in prev_ctx else [], uri={
                        'type': args[0],
                        'id': item
                    })
                else:
                    await ctx.message.reply("{0}: Index {1} is out of range.".format(ctx.author.mention, index + 1))
            else:
                await ctx.message.reply("{}: Invalid search context, please try recommending again.".format(ctx.author.mention))
        else:
            await ctx.message.reply("{}: Incomplete command.".format(ctx.author.mention))
        self.__clear_search_context(ctx.author)


    @commands.command()
    async def list(self, ctx):
        """List stuff recommended to you."""
        await self.__get_recommendations(ctx, str(ctx.author.id), ctx.author.name, "Your", ctx.author.avatar_url)


    @commands.command()
    async def listsvr(self, ctx):
        """List stuff recommended to everyone on the server."""
        await self.__get_recommendations(ctx, "server", ctx.guild.name, "This server's", Embed.Empty)


    @commands.command(aliases=['clr'])
    async def clear(self, ctx):
        """Clear your recommendations."""
        self.db.child("recommendations").child(str(ctx.guild.id)).child(str(ctx.author.id)).remove()
        await ctx.message.reply("Cleared recommendations for {}.".format(ctx.author.mention))


    @commands.command(aliases=['clrsvr'])
    async def clearsvr(self, ctx):
        """Clear the server recommendations."""
        if ctx.author.guild_permissions.administrator:
            self.db.child("recommendations").child(str(ctx.guild.id)).child("server").remove()
            await ctx.message.reply("{}: Cleared server recommendations.".format(ctx.author.mention))
        else:
            await ctx.message.reply("{}, only administrators can clear server recommendations.".format(ctx.author.mention))
