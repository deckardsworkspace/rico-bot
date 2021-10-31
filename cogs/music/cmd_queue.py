from collections import deque
from nextcord import Color, Embed
from nextcord.ext.commands import command, Context
from typing import List
from util import list_chunks, Paginator
from .queue_helpers import get_queue_index, get_queue_db, set_queue_db
import random


@command(name='clearqueue', aliases=['cq'])
async def clear_queue(self, ctx: Context):
    # Empty queue in DB
    set_queue_db(self.db, str(ctx.guild.id), deque([]))
    return await ctx.reply(f'**:wastebasket: | Cleared the queue for {ctx.guild.name}**')


@command(aliases=['q'])
async def queue(self, ctx: Context):
    db_queue = get_queue_db(self.db, str(ctx.guild.id))

    # Get now playing index
    current_i = -1
    current_info = ()
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)
    if player.current is not None:
        current_i = get_queue_index(self.db, str(ctx.guild.id))

        # Get now playing info
        stored_info = player.fetch(player.current.identifier)
        if stored_info is not None and 'title' in stored_info:
            # Spotify info available for current track
            current_info = (stored_info['title'], stored_info['author'])

    if not len(db_queue):
        embed = Embed(color=Color.lighter_grey())
        embed.title = 'Queue is empty'
        return await ctx.reply(embed=embed)
    else:
        # Create paginated embeds
        paginator = Paginator(ctx)
        home_chunk = 0
        count = 1
        embeds: List[Embed] = []
        embed_title = f'Queue for {ctx.guild.name}'
        embed_desc = f'{len(db_queue)} items total'

        for i, chunk in enumerate(list_chunks(list(db_queue))):
            embed = Embed(title=embed_title, description=embed_desc, color=Color.lighter_gray())

            for track in chunk:
                artist = 'Unknown'
                if track.spotify_id is not None:
                    title = track.title
                    artist = track.artist
                elif track.url is not None:
                    title = track.url
                else:
                    title = track.query.replace('ytsearch:', '')
                
                if len(current_info) and count - 1 == current_i:
                    # Add now playing emoji and index
                    title = f'▶️ | {count}. {current_info[0]}'
                    artist = current_info[1]
                    home_chunk = i
                else:
                    # Add index only
                    title = f'{count}. {title}'

                embed.add_field(name=title, value=artist, inline=False)
                count += 1

            embeds.append(embed)

        if len(embeds) > 1:
            return await paginator.run(embeds, start=home_chunk)
        return await ctx.send(embed=embeds[0])


@command(name='removequeue', aliases=['rmq'])
async def remove_from_queue(self, ctx: Context, *, query: str):
    async with ctx.typing():
        db_queue = get_queue_db(self.db, str(ctx.guild.id))
        
        # Parse all positions
        try:
            positions = list(map(lambda x: int(x) - 1, query.split(' ')))
        except ValueError as e:
            return await ctx.reply(f'Please check your input - this command only accepts numbers.\n`{e}`')
        
        # Sort positions in descending order so we can remove them
        # one by one without messing up the indexing
        positions.sort(reverse=True)

        # Start dequeueing
        dequeued = 0
        embed = Embed(color=Color.greyple(), title='Removed from queue')
        for i in positions:
            if i > len(db_queue) or i < 0:
                await ctx.send(f'Cannot remove song {i + 1} as it is out of range.')
                continue

            dequeued = dequeued + 1
            del db_queue[i]

        if dequeued:
            # At least one song was removed from the queue
            embed.description = f'{dequeued} track(s)'
            set_queue_db(self.db, str(ctx.guild.id), db_queue)
            return await ctx.reply(embed=embed)


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
