from asyncio.exceptions import TimeoutError
from nextcord import Embed
from nextcord.ext.commands import Bot, Context
from pyrebase.pyrebase import Database
from typing import Dict, List
from util import dict_chunks, reconstruct_url, Paginator


async def add(ctx: Context, db: Database, mentions: List[int], rec: Dict):
    """Add recommendation to list. If uri is specified, recommendation details are pulled from Spotify."""
    if not len(mentions):
        recipient = "the server"
        add_recommendation(db, ctx.guild.id, rec, server=True)
    else:
        recipients = []
        for user in mentions:
            recipients.append("<@{0}>".format(user))
            add_recommendation(db, user, rec, server=False)
        recipient = ", ".join(recipients)

    success = ":white_check_mark: Recommended '**{0}**' to {1}".format(rec['name'], recipient)
    await ctx.reply(success)


def add_recommendation(db: Database, entity_id: int, rec: Dict, server: bool = False):
    db.child("recommendations").child("server" if server else "user").child(str(entity_id)).push(rec)


async def create_remove_dialog(client: Bot, ctx: Context,
                               server: bool = False, field_name: str = None, field_value: str = None):
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
        reaction, _ = await client.wait_for("reaction_add", timeout=10.0, check=check)

        if str(reaction.emoji) == up:
            await dialog.delete()
            return True
        elif str(reaction.emoji) == down:
            await dialog.delete()
            await ctx.send("{}: Got it, not removing.".format(ctx.author.mention))
    except TimeoutError:
        await dialog.remove_reaction(up, client.user)
        await dialog.remove_reaction(down, client.user)
        await ctx.send("{}: Timed out, not removing.".format(ctx.author.mention))
    return False


def get_raw_recommendations(db: Database, entity_id: int, server: bool = False):
    return db.child("recommendations").child("server" if server else "user").child(str(entity_id))


async def get_recommendations(ctx: Context, db: Database, name: str, image: str,
                              server: bool = False, entity_id: str = ""):
    # Get all recommendations for user/server
    entity = ctx.guild.id if server else entity_id
    rec_list = get_raw_recommendations(db, entity, server=server).get().val()
    index = 1

    if rec_list and len(rec_list.keys()):
        # Create paginated embeds
        paginator = Paginator(ctx)
        embeds = []
        embed_title = "Recommendations for {}".format(name)
        embed_desc = "{} item(s) total".format(len(rec_list.keys()))

        for chunk in dict_chunks(rec_list):
            embed = Embed(title=embed_title, color=0x20ce09)
            embed.set_author(name=embed_desc, icon_url=image)
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

        if len(embeds) > 1:
            await paginator.run(embeds)
        else:
            await ctx.send(embed=embeds[0])
    else:
        await ctx.reply("Recommendation list for {} is currently empty.".format(name))


async def remove_recommendation(client: Bot, db: Database, ctx: Context, index: int, server: bool = False):
    # Check if user has recommendations and if requested index is in range
    entity_id = ctx.guild.id if server else ctx.author.id
    owner = "the server's" if server else "{}'s".format(ctx.author.mention)
    rec_list = get_raw_recommendations(db, entity_id, server=server).get().val()

    if rec_list and len(rec_list):
        if len(rec_list) >= index:
            index = list(rec_list.keys())[index - 1]
            rec_name = rec_list[index]['name']
            recommender = "Added by {}".format(rec_list[index]['recommender'])

            if await create_remove_dialog(client, ctx, server, rec_name, recommender):
                get_raw_recommendations(db, entity_id, server=server).child(index).remove()
                await ctx.reply(":white_check_mark: Removed **'{0}'** from {1} list".format(rec_name, owner))

        else:
            await ctx.reply("Index {} is out of range.".format(index))
    else:
        await ctx.reply("Nothing found in {} list.".format(owner))
