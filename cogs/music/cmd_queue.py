from collections import deque
from DiscordUtils.Pagination import AutoEmbedPaginator
from nextcord import Color, Embed
from nextcord.ext.commands import command, Context
from util import list_chunks
from .queue_helpers import get_queue_db, set_queue_db
import random


@command(name='clearqueue', aliases=['cq'])
async def clear_queue(self, ctx: Context):
    # Empty queue in DB
    set_queue_db(self.db, str(ctx.guild.id), deque([]))
    return await ctx.reply(f'**:wastebasket: | Cleared the queue for {ctx.guild.name}**')


@command(aliases=['q'])
async def queue(self, ctx: Context):
    db_queue = get_queue_db(self.db, str(ctx.guild.id))

    # Add now playing to queue
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)
    if player.current is not None:
        # Get now playing info
        current_id = player.current.identifier
        stored_info = player.fetch(current_id)
        if stored_info and 'title' in stored_info:
            stored_info['info'] = {
                'title': stored_info['title'],
                'author': stored_info['author']
            }
            db_queue.appendleft(stored_info)

    if not len(db_queue):
        embed = Embed(color=Color.lighter_grey())
        embed.title = 'Queue is empty'
        return await ctx.reply(embed=embed)
    else:
        # Create paginated embeds
        paginator = AutoEmbedPaginator(ctx)
        count = 1
        embeds = []
        embed_title = f'Queue for {ctx.guild.name}'
        embed_desc = f'{len(db_queue)} items total'

        for chunk in list_chunks(list(db_queue)):
            embed = Embed(title=embed_title, description=embed_desc, color=Color.lighter_gray())
            embed.set_thumbnail(url=ctx.guild.icon.url)

            tracks = []
            for track in chunk:
                if 'spotify' in track:
                    track_name = track['spotify']['name']
                    track_artist = track['spotify']['artist']
                else:
                    track_name = track['info']['title']
                    track_artist = track['info']['author']
                
                if count == 1 and player.current is not None:
                    field_name = f'Now playing\n{track_name}'
                else:
                    if player.current is not None:
                        field_name = f'{count - 1} - {track_name}'
                    else:
                        field_name = f'{count} - {track_name}'
                embed.add_field(name=field_name, value=track_artist, inline=False)
                count = count + 1
            
            embed.description = '\n\n'.join(tracks)
            embeds.append(embed)

        if len(embeds) > 1:
            return await paginator.run(embeds)
        return ctx.send(embed=embeds[0])


@command(aliases=['shuf'])
async def shuffle(self, ctx: Context):
    async with ctx.typing():
        db_queue = get_queue_db(self.db, str(ctx.guild.id))
        if not len(db_queue):
            return await ctx.reply('The queue is empty. Nothing to shuffle.')

        random.shuffle(db_queue)
        set_queue_db(self.db, str(ctx.guild.id), db_queue)
        embed = Embed(color=Color.gold())
        embed.title = 'Shuffled the queue'
        embed.description = f'{len(db_queue)} tracks shuffled'
        return await ctx.reply(embed=embed)
