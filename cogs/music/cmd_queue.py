from collections import deque
from nextcord import Color, Message
from nextcord.ext.commands import command, Context
from typing import Optional
from util import list_chunks, RicoEmbed, Paginator
from .queue_helpers import (
    get_loop_all, get_queue_index, get_queue_db, get_shuffle_indices,
    set_queue_db, set_queue_index, set_shuffle_indices
)
import random


async def send_invalid_arg(ctx: Context, err: str, e: Optional[Exception] = None) -> Message:
    err_desc = [err]
    if e is not None:
        err_desc.append(f'`{e}`')

    embed = RicoEmbed(
        color=Color.red(),
        title=f':x:｜Invalid arguments',
        description=err_desc
    )
    return await embed.send(ctx, as_reply=True)


@command(name='clearqueue', aliases=['cq'])
async def clear_queue(self, ctx: Context):
    # Empty queue in DB
    set_queue_db(self.db, str(ctx.guild.id), [])
    set_shuffle_indices(self.db, str(ctx.guild.id), [])
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
            if dest + 1 < 0 or dest + 1 > len(db_queue):
                return await send_invalid_arg(ctx, f'Destination `{positions[1]}` is out of range (1 to {len(db_queue)}).')
        except ValueError as e:
            return await send_invalid_arg(ctx, 'This command only accepts integers.', e)

        # Move track
        shuffle_indices = get_shuffle_indices(self.db, str(ctx.guild.id))
        if len(shuffle_indices) > 0:
            # Shuffling does not touch the original queue,
            # so we can simply reorder the indices.
            src_item = db_queue[shuffle_indices[src]]
            shuffle_indices.insert(dest, shuffle_indices.pop(src))
            set_shuffle_indices(self.db, str(ctx.guild.id), shuffle_indices)
        else:
            # Check if we need to adjust current position
            current_i = get_queue_index(self.db, str(ctx.guild.id))
            if isinstance(current_i, int) and dest <= current_i:
                # Track will be moved to before the current track.
                # Increment the current position.
                set_queue_index(self.db, str(ctx.guild.id), current_i + 1)

            # Remove track at source first...
            src_item = db_queue[src]
            del db_queue[src]

            # ...then insert at destination
            db_queue.insert(dest, src_item)
            set_queue_db(self.db, str(ctx.guild.id), db_queue)

        # Success!
        title, artist = src_item.get_details()
        embed = RicoEmbed(
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
async def queue(self, ctx: Context, *, query: str = None):
    # Catch users trying to add to queue using this command
    if query is not None:
        # Give them a tip
        embed = RicoEmbed(
            title=':information_source:｜Tip',
            description=[
                'You can use the `play`/`p` command to play tracks!',
                'This command (`queue`/`q`) is for listing the current queue.'
            ],
            color=Color.lighter_gray()
        )
        await embed.send(ctx, as_reply=True)

        # Let's invoke the play command for them
        cmd = self.bot.get_command('play')
        return await ctx.invoke(cmd, query)

    # Get queue from DB
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
        embed = RicoEmbed(
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

        # Show shuffled queue if applicable
        shuffle_indices = get_shuffle_indices(self.db, str(ctx.guild.id))
        shuffled = len(shuffle_indices) > 0
        if shuffled:
            current_i = shuffle_indices.index(current_i)
            embed_desc.append('Queue is shuffled :twisted_rightwards_arrows:')

        # Split queue into chunks of 10 tracks each
        chunks = list_chunks([db_queue[i] for i in shuffle_indices]) if shuffled else list_chunks(db_queue)

        for i, chunk in enumerate(chunks):
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

            embed = RicoEmbed(
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
        shuffle_indices = get_shuffle_indices(self.db, str(ctx.guild.id))
        
        # Parse all positions
        try:
            positions = list(map(lambda x: int(x) - 1, query.split(' ')))

            if len(shuffle_indices) > 0:
                # Translate positions to their shuffled equivalents
                positions = [shuffle_indices[i] for i in positions]
        except ValueError as e:
            return await send_invalid_arg(ctx, e)
        
        # Sort positions in descending order so we can remove them
        # one by one without messing up the indexing
        positions.sort(reverse=True)

        # Start dequeueing
        dequeued = []
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
            
            # Remove from queue and shuffle indices
            dequeued.append(i)
            del db_queue[i]
            if len(shuffle_indices):
                shuffle_indices.remove(i)

        if len(dequeued):
            # At least one song was removed from the queue
            set_queue_db(self.db, str(ctx.guild.id), db_queue)

            # Adjust current position and shuffle indices
            if isinstance(current_i, int):
                set_queue_index(self.db, str(ctx.guild.id), current_i - adjust_current)
                if len(shuffle_indices):
                    for i in dequeued:
                        # Terribly inefficient, but I can't think of a better way right now...
                        shuffle_indices = [j - 1 if j > i else j for j in shuffle_indices]
                    set_shuffle_indices(self.db, str(ctx.guild.id), shuffle_indices)

            # Update user
            embed = RicoEmbed(
                color=Color.orange(),
                title=f':white_check_mark:｜Removed from queue',
                description=f'{len(dequeued)} track(s)'
            )
            return await embed.send(ctx, as_reply=True)


@command(aliases=['shuf'])
async def shuffle(self, ctx: Context):
    async with ctx.typing():
        db_queue = get_queue_db(self.db, str(ctx.guild.id))
        if not len(db_queue):
            embed = RicoEmbed(
                color=Color.red(),
                title=':x:｜Queue is empty',
                description='There is nothing to shuffle!'
            )
            return await embed.send(ctx, as_reply=True)
        
        # Are we already shuffling?
        reshuffle = len(get_shuffle_indices(self.db, str(ctx.guild.id))) > 0
        action = 'Reshuffled' if reshuffle else 'Shuffled'

        # Shuffle indices
        current_i = get_queue_index(self.db, str(ctx.guild.id))
        indices = [i for i in range(len(db_queue)) if i != current_i]
        random.shuffle(indices)

        # Put current track at the start of the list
        indices.insert(0, current_i)

        # Save shuffled indices to db
        set_shuffle_indices(self.db, str(ctx.guild.id), indices)

        # Send reply
        embed = RicoEmbed(
            color=Color.gold(),
            title=f':twisted_rightwards_arrows:｜{action} the queue',
            description=f'{len(db_queue)} tracks shuffled. To unshuffle, use the `unshuffle` command.'
        )
        return await embed.send(ctx, as_reply=True)


@command(aliases=['unshuf'])
async def unshuffle(self, ctx: Context):
    async with ctx.typing():
        # Are we even shuffling?
        shuffling = len(get_shuffle_indices(self.db, str(ctx.guild.id))) > 0
        if not shuffling:
            embed = RicoEmbed(
                color=Color.red(),
                title=':x:｜Queue is not shuffled'
            )
            return await embed.send(ctx, as_reply=True)

        # Remove shuffle indices from db
        set_shuffle_indices(self.db, str(ctx.guild.id), [])

        # Send reply
        embed = RicoEmbed(
            color=Color.gold(),
            title=':twisted_rightwards_arrows:｜Queue is no longer shuffled'
        )
        return await embed.send(ctx, as_reply=True)
