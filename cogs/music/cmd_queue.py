from collections import deque
from nextcord import Color, Message
from nextcord.ext.commands import command, Context
from typing import Optional
from util import list_chunks, MusicEmbed, Paginator
from .queue_helpers import get_loop_all, get_queue_index, get_queue_db, set_queue_db, set_queue_index
import random


async def send_invalid_arg(ctx: Context, err: str, e: Optional[Exception] = None) -> Message:
    err_desc = [err]
    if e is not None:
        err_desc.append(f'`{e}`')

    embed = MusicEmbed(
        color=Color.red(),
        title=f':x:｜Invalid arguments',
        description=err_desc
    )
    return await embed.send(ctx, as_reply=True)


@command(name='clearqueue', aliases=['cq'])
async def clear_queue(self, ctx: Context):
    # Empty queue in DB
    set_queue_db(self.db, str(ctx.guild.id), [])
    return await ctx.reply(f'**:wastebasket:｜Cleared the queue for {ctx.guild.name}**')


@command(aliases=['m'])
async def move(self, ctx: Context, *, positions: str = None):
    async with ctx.typing():
        db_queue = get_queue_db(self.db, str(ctx.guild.id))
        
        # Parse all positions
        positions = positions.split()
        if len(positions) != 2:
            return await send_invalid_arg(ctx, 'Please specify a source and destination position.')
        try:
            src = int(positions[0]) - 1
            dest = int(positions[1]) - 1

            if src == dest:
                return await send_invalid_arg(ctx, 'Cannot move item to the same spot.')
            if dest + 1 < 0 or dest + 1 >= len(db_queue):
                return await send_invalid_arg(ctx, f'Destination `{positions[1]}` is out of range (1 to {len(db_queue)}).')
        except ValueError as e:
            return await send_invalid_arg(ctx, 'This command only accepts integers.', e)
        
        # Check if we need to adjust current position
        current_i = get_queue_index(self.db, str(ctx.guild.id))
        if isinstance(current_i, int) and dest <= current_i:
            # Track will be moved to before the current track.
            # Increment the current position.
            set_queue_index(self.db, str(ctx.guild.id), current_i + 1)

        # Move track
        # Remove track at index first...
        src_item = db_queue[src]
        title, artist = src_item.get_details()
        del db_queue[src]
        # ...then insert at destination
        db_queue.insert(dest, src_item)

        # Success!
        set_queue_db(self.db, str(ctx.guild.id), db_queue)
        embed = MusicEmbed(
            color=Color.orange(),
            title=f':white_check_mark:｜Moved track',
            description=[
                f'**{title}**',
                artist,
                f'Now at position **{dest + 1}**'
            ]
        )
        return await embed.send(ctx, as_reply=True)


@command(aliases=['q'])
async def queue(self, ctx: Context):
    # Delete the previous now playing message
    try:
        old_message_id = self.db.child('player').child(str(ctx.guild.id)).child('qmessage').get().val()
        if old_message_id:
            old_message = await ctx.fetch_message(int(old_message_id))
            await old_message.delete()
    except:
        pass

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

    # Display queue
    db_queue = get_queue_db(self.db, str(ctx.guild.id))
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
                title, artist = track.get_details()
                
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

        # Save this message
        def save_msg(msg_id: int):
            self.db.child('player').child(str(ctx.guild.id)).child('qmessage').set(str(msg_id))
        if len(embeds) > 1:
            return await paginator.run(embeds, start=home_chunk, callback=save_msg)
        message = await ctx.send(embed=embeds[0])
        return save_msg(message.id)


@command(name='removequeue', aliases=['rmq'])
async def remove_from_queue(self, ctx: Context, *, query: str):
    async with ctx.typing():
        db_queue = get_queue_db(self.db, str(ctx.guild.id))
        
        # Parse all positions
        try:
            positions = list(map(lambda x: int(x) - 1, query.split(' ')))
        except ValueError as e:
            return await send_invalid_arg(ctx, e)
        
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
