from collections import deque
from nextcord import Color
from nextcord.ext.commands import command, Context
from util import list_chunks, MusicEmbed, Paginator
from .queue_helpers import get_loop_all, get_queue_index, get_queue_db, set_queue_db, set_queue_index
import random


@command(name='clearqueue', aliases=['cq'])
async def clear_queue(self, ctx: Context):
    # Empty queue in DB
    set_queue_db(self.db, str(ctx.guild.id), deque([]))
    return await ctx.reply(f'**:wastebasket:｜Cleared the queue for {ctx.guild.name}**')


@command(aliases=['q'])
async def queue(self, ctx: Context):
    db_queue = get_queue_db(self.db, str(ctx.guild.id))

    # Get now playing index
    current_i = -1
    current_info = ()
    player = self.get_player(ctx.guild.id)
    if player.current is not None:
        current_i = get_queue_index(self.db, str(ctx.guild.id))

        # Get now playing info
        stored_info = player.fetch(player.current.identifier)
        if stored_info is not None and 'title' in stored_info:
            # Spotify info available for current track
            current_info = (stored_info['title'], stored_info['author'])

    if not len(db_queue):
        embed = MusicEmbed(
            color=Color.dark_grey(),
            title=f':information_source:｜Queue is empty'
        )
        return await embed.send(ctx, as_reply=True)
    else:
        # Create paginated embeds
        paginator = Paginator(ctx)
        home_chunk = 0
        count = 1
        embeds = []
        embed_title = f'Queue for {ctx.guild.name}'

        # Show loop status
        embed_desc = [f'{len(db_queue)} item(s) total']
        loop_all = get_loop_all(self.db, str(ctx.guild.id))
        if loop_all:
            embed_desc.append('Looping the whole queue :repeat:')

        for i, chunk in enumerate(list_chunks(list(db_queue))):
            fields = []

            for track in chunk:
                if track.spotify_id is not None:
                    title = track.title
                    artist = f'by {track.artist}'
                elif track.url is not None:
                    title = track.url
                    artist = 'Direct link'
                else:
                    title = track.query.replace('ytsearch:', '')
                    artist = 'Search query'
                
                if len(current_info) and count - 1 == current_i:
                    # Add now playing emoji and index
                    emoji = ':repeat:' if player.repeat else ':arrow_forward:'
                    title = f'{emoji}｜{count}. {current_info[0]}'
                    artist = f'by {current_info[1]}'
                    home_chunk = i
                else:
                    # Add index only
                    title = f'{count}. {title}'

                fields.append([title, artist])
                count += 1

            embed = MusicEmbed(
                title=embed_title,
                description=embed_desc,
                thumbnail_url=ctx.guild.icon.url,
                color=Color.lighter_gray(),
                fields=fields
            )
            embeds.append(embed.get())

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
            embed = MusicEmbed(
                color=Color.red(),
                title=f':x:｜Invalid arguments',
                description=[
                    'This command only accepts integers.',
                    f'`ValueError: {e}`'
                ]
            )
            return await embed.send(ctx, as_reply=True)
        
        # Sort positions in descending order so we can remove them
        # one by one without messing up the indexing
        positions.sort(reverse=True)

        # Start dequeueing
        dequeued = 0
        current_i = get_queue_index(self.db, str(ctx.guild.id))
        adjust_current = 0
        for i in positions:
            if i > len(db_queue) or i < 0:
                await ctx.send(f'Cannot remove song {i + 1} as it is out of range.')
                continue

            # Adjust current position
            if isinstance(current_i, int):
                if current_i == i:
                    await ctx.send(f'Cannot remove currently playing song {i + 1}.')
                    continue
                if current_i > i:
                    # We are removing songs from the past,
                    # so we decrement the current position by 1
                    # to allow backward seeks to work properly.
                    adjust_current += 1
            
            # Remove from queue
            dequeued = dequeued + 1
            del db_queue[i]

        if dequeued:
            # At least one song was removed from the queue
            set_queue_db(self.db, str(ctx.guild.id), db_queue)

            # Adjust current position if applicable
            if isinstance(current_i, int) and adjust_current > 0:
                set_queue_index(self.db, str(ctx.guild.id), current_i - adjust_current)

            embed = MusicEmbed(
                color=Color.orange(),
                title=f':white_check_mark:｜Removed from queue',
                description=f'{dequeued} track(s)'
            )
            return await embed.send(ctx, as_reply=True)


@command(aliases=['shuf'])
async def shuffle(self, ctx: Context):
    async with ctx.typing():
        db_queue = get_queue_db(self.db, str(ctx.guild.id))
        if not len(db_queue):
            embed = MusicEmbed(
                color=Color.red(),
                title=':x:｜Queue is empty',
                description='There is nothing to shuffle!'
            )
            return await embed.send(ctx, as_reply=True)

        # Shuffle whole queue
        # TODO: Shuffle a list of indices instead,
        #       so we can undo the shuffle.
        random.shuffle(db_queue)
        set_queue_db(self.db, str(ctx.guild.id), db_queue)

        # Send reply
        embed = MusicEmbed(
            color=Color.gold(),
            title=':twisted_rightwards_arrows:｜Shuffled the queue',
            description=f'{len(db_queue)} tracks shuffled'
        )
        return await embed.send(ctx, as_reply=True)
