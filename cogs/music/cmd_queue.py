from collections import deque
from DiscordUtils.Pagination import AutoEmbedPaginator
from lavalink.models import AudioTrack, DefaultPlayer
from nextcord import Color, Embed
from nextcord.ext.commands import command, Context
from util import list_chunks
from .lavalink_client import LavalinkVoiceClient
import random


async def search(player: DefaultPlayer, query: str = None):
    # Get the results for the query from Lavalink
    result = await player.node.get_tracks(query)
    return result


@command(name='clearqueue', aliases=['cq'])
async def clear_queue(self, ctx: Context):
    # Empty queue in DB
    self.set_queue_db(str(ctx.guild.id), deque([]))
    return await ctx.reply(f'**:wastebasket: | Cleared the queue for {ctx.guild.name}**')


async def enqueue(self, query: str, ctx: Context, sp_data: dict = None,
                  queue_to_db: bool = None, quiet: bool = False) -> bool:
    # Get the player for this guild from cache
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)

    # Get the results for the query from Lavalink
    results = await search(player, query)

    # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
    # Alternatively, results['tracks'] could be an empty array if the query yielded no tracks.
    if not results or not results['tracks']:
        if not quiet:
            await ctx.send(f'Nothing found for `{query}`!')
        return False
    else:
        # If a result is found, connect to voice.
        if not player.is_connected:
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)

    # Save to DB if player is not idle.
    queue_to_db = queue_to_db if queue_to_db is not None else player.current is not None

    embed = Embed(color=Color.blurple())

    # Valid loadTypes are:
    #   TRACK_LOADED    - single video/direct URL
    #   PLAYLIST_LOADED - direct URL to playlist
    #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
    #   NO_MATCHES      - query yielded no results
    #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
    if results['loadType'] == 'PLAYLIST_LOADED':
        tracks = results['tracks']

        if queue_to_db:
            # Add all results to database queue
            for i in range(len(tracks)):
                tracks[i]['requester'] = ctx.author.id
            self.enqueue_db(str(ctx.guild.id), tracks)
        else:
            # Add all of the tracks from the playlist to the queue
            for track in tracks:
                # Save track metadata to player storage
                if 'identifier' in track['info']:
                    player.store(track['info']['identifier'], track['info'])

                player.add(requester=ctx.author.id, track=track)

        embed.title = 'Playlist enqueued'
        embed.description = f'{results["playlistInfo"]["name"]} - {len(tracks)} tracks'
    else:
        track = results['tracks'][0]
        embed.title = 'Track enqueued'
        embed.description = f'[{track["info"]["title"]}]({track["info"]["uri"]})'

        # Add Spotify info to track
        if sp_data is not None:
            track['info']['spotify'] = sp_data

        if queue_to_db:
            # Add track to database queue
            track['requester'] = ctx.author.id
            self.enqueue_db(str(ctx.guild.id), track)
        else:
            # Save track metadata to player storage
            if 'identifier' in track['info']:
                player.store(track['info']['identifier'], track['info'])

            # Add track directly to Lavalink queue
            track = AudioTrack(track, ctx.author.id)
            player.add(requester=ctx.author.id, track=track)

    # We don't want to call .play() if the player is not idle
    # as that will effectively skip the current track.
    if not player.is_playing and not player.paused:
        await player.play()
    if not quiet:
        await ctx.send(embed=embed)
    
    return True


@command(aliases=['q'])
async def queue(self, ctx: Context):
    db_queue = self.get_queue_db(str(ctx.guild.id))

    # Add now playing to queue
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)
    if player.current is not None:
        # Get now playing info
        current_id = player.current.identifier
        stored_info = player.fetch(current_id)
        if stored_info and 'title' in stored_info:
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

        for chunk in list_chunks(db_queue):
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

        return await paginator.run(embeds)

@command(aliases=['shuf'])
async def shuffle(self, ctx: Context):
    async with ctx.typing():
        queue = self.get_queue_db(str(ctx.guild.id))
        if not len(queue):
            return await ctx.reply('The queue is empty. Nothing to shuffle.')

        random.shuffle(queue)
        self.set_queue_db(str(ctx.guild.id), queue)
        embed = Embed(color=Color.gold())
        embed.title = 'Shuffled the queue'
        embed.description = f'{len(queue)} tracks shuffled'
        return await ctx.reply(embed=embed)
