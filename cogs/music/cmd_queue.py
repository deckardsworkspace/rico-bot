from collections import deque
from lavalink.models import AudioTrack, DefaultPlayer
from nextcord import Color, Embed
from nextcord.ext.commands import command, Context
from util import ellipsis_truncate, QueueEmptyError
from .lavalink_client import LavalinkVoiceClient


@command(name='clearqueue', aliases=['cq'])
async def clear_queue(self, ctx: Context):
    # Empty queue in DB
    self.set_queue_db(str(ctx.guild.id), deque([]))
    return await ctx.reply(f'**:wastebasket: | Cleared the queue for {ctx.guild.name}**')


async def enqueue(self, query: str, player: DefaultPlayer, ctx: Context,
                  queue_to_db: bool = False, quiet: bool = False) -> bool:
    # Get the results for the query from Lavalink.
    results = await player.node.get_tracks(query)

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
    queue_to_db = queue_to_db or player.current is not None
    if queue_to_db:
        self.enqueue_db(str(ctx.guild.id), query)

    embed = Embed(color=Color.blurple())

    # Valid loadTypes are:
    #   TRACK_LOADED    - single video/direct URL
    #   PLAYLIST_LOADED - direct URL to playlist
    #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
    #   NO_MATCHES      - query yielded no results
    #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
    if results['loadType'] == 'PLAYLIST_LOADED':
        tracks = results['tracks']

        # Add all of the tracks from the playlist to the queue
        if not queue_to_db:
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

        # Add track to the queue, if the queue is empty.
        if not queue_to_db:
            # Save track metadata to player storage
            if 'identifier' in track['info']:
                player.store(track['info']['identifier'], track['info'])

            track = AudioTrack(track, ctx.author.id)
            player.add(requester=ctx.author.id, track=track)

    if not quiet:
        await ctx.send(embed=embed)

    # We don't want to call .play() if the player is not idle
    # as that will effectively skip the current track.
    if not player.is_playing and not player.paused:
        await player.play()
    
    return True


@command(aliases=['q'])
async def queue(self, ctx: Context):
    # Get the player for this guild from cache.
    player = self.bot.lavalink.player_manager.get(ctx.guild.id)
    await ctx.send(f'Native Lavalink queue: `{player.queue}`')
    try:
        db_queue = self.get_queue_db(str(ctx.guild.id))
        await ctx.send(f'Firebase DB queue: `{ellipsis_truncate(str(db_queue), 1500)}`')
    except QueueEmptyError:
        await ctx.send(f'Firebase DB queue is empty')
