from collections import deque
from nextcord import Color, Embed
from nextcord.ext.commands import command, Context
from util import check_url, check_spotify_url, check_twitch_url, check_youtube_url, parse_spotify_url
from util import QueueEmptyError, SpotifyInvalidURLError


@command(name='nowplaying', aliases=['np'])
async def now_playing(self, ctx: Context, title: str = None):
    # Delete the previous now playing message
    try:
        old_message_id = self.db.child('player').child(str(ctx.guild.id)).child('npmessage').get().val()
        if old_message_id:
            old_message = await ctx.fetch_message(int(old_message_id))
            await old_message.delete()
    except Exception as e:
        print(f'Error while trying to delete old npmsg: {e}')

    # Get the player for this guild from cache
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)

    if player.is_playing or player.paused:
        embed = Embed(color=Color.teal())
        embed.title = 'Now playing' if player.is_playing else 'Paused'
        embed.description = title if title else player.current.title
    else:
        embed = Embed(color=Color.yellow())
        embed.title = 'Not playing'
        embed.description = 'To play, use `{0}play <URL/search term>`. Try `{0}help` for more.'.format('rc!')

    # Save this message
    if title:
        message = await ctx.send(embed=embed)
    else:
        message = await ctx.reply(embed=embed)
    self.db.child('player').child(str(ctx.guild.id)).child('npmessage').set(str(message.id))


@command()
async def pause(self, ctx: Context):
    # Get the player for this guild from cache.
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)

    # Pause the player.
    if not player.paused:
        await player.set_pause(pause=True)
        await ctx.reply('Paused the player.')
    else:
        await ctx.reply('Already paused.')


@command(aliases=['p'])
async def play(self, ctx: Context, *, query: str = None):
    """ Searches and plays a song from a given query. """
    async with ctx.typing():
        # Get the player for this guild from cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Pick up where we left off
        if not query:
            old_np = self.db.child('player').child(str(ctx.guild.id)).child('np').get().val()
            if old_np:
                embed = Embed(color=Color.purple())
                embed.title = 'Resuming interrupted queue'
                embed.description = old_np
                await ctx.reply(embed=embed)
                return await self.enqueue(f'ytsearch:{old_np}', player, ctx=ctx, quiet=True)
            return await ctx.reply('Please specify a URL or a search term to play.')

        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip('<>')

        # Query is not a URL. Have Lavalink do a YouTube search for it.
        if not check_url(query):
            return await self.enqueue(f'ytsearch:{query}', player, ctx=ctx)

        # Query is a URL.
        if check_spotify_url(query):
            # Query is a Spotify URL.
            try:
                sp_type, sp_id = parse_spotify_url(query, valid_types=['track', 'album', 'playlist'])
            except SpotifyInvalidURLError:
                return await ctx.reply('Only Spotify track, album, and playlist URLs are supported.')

            if sp_type == 'track':
                # Get track details from Spotify
                track_name, track_artist = self.spotify.get_track(sp_id)
                return await self.enqueue(f'ytsearch:{track_name} {track_artist}', player, ctx=ctx)
            else:
                # Get playlist or album tracks from Spotify
                list_name, list_author, tracks = self.spotify.get_tracks(sp_type, sp_id)
                track_queue = deque(tracks)

                if len(tracks) < 1:
                    # No tracks
                    return await ctx.reply(f'Spotify {sp_type} is empty.')
                elif len(tracks) == 1:
                    # Single track
                    return await self.enqueue(f'ytsearch:{tracks[0][0]} {tracks[0][1]}', player, ctx=ctx)
                else:
                    # Multiple tracks
                    # There is no way to queue multiple items in one batch through Lavalink.py,
                    # and performing a search takes time which adds up as playlists grow larger.
                    # Hence, to allow the user to start listening immediately,
                    # we play the first one and store the rest of the queue in DB for later.
                    await ctx.reply(f':arrow_forward: | Enqueueing {sp_type}, this might take a while...')

                    queries = []
                    success = False
                    while len(track_queue):
                        track = track_queue.popleft()
                        track_query = f'ytsearch:{track[0]} {track[1]}'

                        if not success:
                            # Enqueue the first valid track
                            success = await self.enqueue(track_query, player, ctx=ctx, quiet=True)
                            if not success:
                                await ctx.send(f'Error enqueueing "{track[0]}".')
                        else:
                            # Append the rest to the queue
                            queries.append(track_query)
                    else:
                        if len(queries):
                            # Append everything in one go to save DB accesses
                            self.enqueue_db_multiple(str(ctx.guild.id), queries)

                    # Send enqueued embed
                    embed = Embed(color=Color.blurple())
                    embed.title = f'Spotify {sp_type} enqueued'
                    embed.description = f'[{list_name}]({query}) by {list_author} ({len(tracks)} tracks)'
                    return await ctx.reply(embed=embed)
        elif check_twitch_url(query) or check_youtube_url(query):
            return await self.enqueue(query, player, ctx=ctx)
        else:
            return await self.enqueue(f'ytsearch:{query}', player, ctx=ctx)


@command(aliases=['shuf'])
async def shuffle(self, ctx: Context):
    try:
        async with ctx.typing():
            queue = self.get_queue_db(str(ctx.guild.id))
            shuffle(queue)
            self.set_queue_db(str(ctx.guild.id), queue)
        await ctx.reply('Queue shuffled.')
    except QueueEmptyError:
        await ctx.reply('The queue is empty. Nothing to shuffle.')


@command(aliases=['next'])
async def skip(self, ctx: Context):
    # Get the player for this guild from cache.
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)

    # Get next in queue.
    try:
        async with ctx.typing():
            while True:
                query = self.dequeue_db(player.guild_id)
                if await self.enqueue(query, player, ctx=ctx, quiet=True):
                    # Skip track.
                    await player.skip()
                    return await ctx.reply('Skipped the track.')
    except QueueEmptyError:
        return await self.disconnect(ctx, reason='Skipped to the end of the queue')


@command()
async def unpause(self, ctx: Context):
    # Get the player for this guild from cache.
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)

    # Unpause the player.
    if player.paused:
        await player.set_pause(pause=False)
        await ctx.reply('Unpaused the player.')
    else:
        await ctx.reply('Already unpaused.')
