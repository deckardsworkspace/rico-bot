from nextcord import Color
from nextcord.ext.commands import command, Context
from util import parse_spotify_url, RicoEmbed, sanitize_youtube_name, SpotifyInvalidURLError
from util.string_util import human_readable_time
from .queue_helpers import (
    enqueue_db, get_queue_size, get_shuffle_indices, set_shuffle_indices,
    QueueItem
)


@command(name='autoplay', aliases=['ap'])
async def autoplay(self, ctx: Context, *, query: str = None):
    """
    Plays a Spotify track, followed by up to 30 recommended tracks.
    The recommended tracks are generated from the specified track
    and up to 4 randomly selected tracks from the user's recent
    playback history.
    """
    async with ctx.typing():
        # Check if the query is a valid Spotify URL/URI
        if not query:
            embed = RicoEmbed(color=Color.red(), title=':x:｜Specify something to play.')
            return await embed.send(ctx, as_reply=True)
        try:
            _, sp_id = parse_spotify_url(query, valid_types=['track'])
        except SpotifyInvalidURLError:
            embed = RicoEmbed(color=Color.red(), title=':x:｜This command only accepts Spotify track URLs.')
            return await embed.send(ctx, as_reply=True)
        
        # Get player
        player = self.get_player(ctx.guild.id)
        is_playing = player is not None and (player.is_playing or player.paused)

        # Play track
        cmd = self.bot.get_command('play')
        await ctx.invoke(cmd, query=query)

        # Get recommendations
        token_data = self.db.child('spotify_auth').child(str(ctx.author.id)).get().val()
        access_token, expires_in, refresh_token, recs = self.spotify.get_recommendations(sp_id, token_data)
        personalized = token_data is not None and 'access_token' in token_data

        # Append tracks to database
        new_tracks = []
        for track in recs:
            track_name, track_artist, track_id, track_duration = track
            new_tracks.append(QueueItem(
                requester=ctx.author.id,
                title=track_name,
                artist=track_artist,
                spotify_id=track_id,
                duration=track_duration
            ))
        enqueue_db(self.db, str(ctx.guild.id), new_tracks)

        # Update shuffle indices, if applicable
        if is_playing:
            shuffle_indices = get_shuffle_indices(self.db, str(ctx.guild.id))
            if len(shuffle_indices) > 0:
                # Append new indices to the end of the list
                old_size = get_queue_size(self.db, str(ctx.guild.id))
                new_indices = [old_size + i for i in range(len(new_tracks))]
                shuffle_indices.extend(new_indices)
                set_shuffle_indices(self.db, str(ctx.guild.id), shuffle_indices)
        
        # Update auth data
        if personalized and access_token != token_data['access_token']:
            self.db.child('spotify_auth').child(str(ctx.author.id)).set({
                'access_token': access_token,
                'expires_in': expires_in,
                'refresh_token': refresh_token
            })
        
        # Send embed
        track_name, track_artist, _, _ = self.spotify.get_track(sp_id)
        embed = RicoEmbed(
            color=Color.green(),
            title=':white_check_mark:｜Recommendations added to queue',
            description=[
                f'based on **{track_name}**',
                f'by **{track_artist}**',
                f'curated for {ctx.author.mention}' if personalized else ''
            ]
        )
        return await embed.send(ctx)


@command(name='recnow', aliases=['rn'])
async def recommend_now_playing(self, ctx: Context):
    # Get the player for this guild from cache
    player = self.get_player(ctx.guild.id)

    # Get recommend command
    cmd = self.bot.get_command('recommend')

    # Get now playing
    if player.current is not None:
        # Recover track info
        current_id = player.current.identifier
        track_info = player.fetch(current_id, None)
        if track_info is not None and hasattr(track_info, 'identifier'):
            spotify_info = player.fetch(f'{track_info.identifier}-spotify', None)
            if spotify_info is not None:
                return await ctx.invoke(cmd, f'spotify:track:{spotify_info["id"]}')
            else:
                track_name = sanitize_youtube_name(track_info['title'])
                return await ctx.invoke(cmd, track_name)
        else:
            embed = RicoEmbed(
                color=Color.red(),
                title=':x:｜Error encountered',
                description='Incomplete or missing info for now playing track.'
            )
            return await embed.send(ctx, as_reply=True)
    else:
        embed = RicoEmbed(
            color=Color.red(),
            title=':x:｜Nothing is playing right now',
            description='Try this command again while Rico is playing music.'
        )
        return await embed.send(ctx, as_reply=True)
