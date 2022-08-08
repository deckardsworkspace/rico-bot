from dataclass.custom_embed import create_error_embed, create_success_embed
from nextcord import Color, Embed, Interaction, slash_command
from nextcord.ext.commands import Cog
from ratelimit import RateLimitException
import requests.exceptions
from typing import TYPE_CHECKING
from util.config import get_debug_guilds
from util.enums import NoteType
from util.string_util import parse_spotify_url
if TYPE_CHECKING:
    from clients.spotify_client import Spotify
    from util.rico_bot import RicoBot


class ExportCog(Cog):
    def __init__(self, bot: 'RicoBot'):
        self._bot = bot
        print(f'Loaded cog: {self.__class__.__name__}')

    @property
    def spotify(self) -> 'Spotify':
        return self._bot.spotify

    @slash_command(name='spotifyexport', guild_ids=get_debug_guilds())
    async def dump_spotify(self, itx: Interaction):
        """
        Export all your recommended Spotify tracks to a new Spotify playlist.
        Requires authentication with Spotify first (`/spotifylogin`).
        """
        await itx.response.defer(ephemeral=True)

        # Get all Spotify tracks recommended to user
        recs = self._bot.api.get_user_notes(itx.user.id)
        tracks = []
        to_remove = []
        for item in recs:
            if item.type == NoteType.SPOTIFY_TRACK:
                _, track_id = parse_spotify_url(item.url)
                tracks.append(f'spotify:track:{track_id}')
                to_remove.append(item.id)

        # Add to playlist
        if len(tracks):
            try:
                result = self._bot.api.export_to_spotify(itx.user.id, tracks)
                playlist_name, playlist_id = result
            except requests.exceptions.HTTPError as e:
                return await itx.followup.send(embed=create_error_embed(
                    title='Could not create Spotify playlist',
                    body=f'`{e}`\nPlease try again later.'
                ))
            except RateLimitException:
                return await itx.followup.send(embed=create_error_embed(
                    title='Rate limit exceeded',
                    body='Please try again later.'
                ))

            # Get playlist art
            icon = self.spotify.get_playlist_cover(playlist_id, default=itx.user.avatar.url)

            # Delete tracks from rec list
            for rec_id in to_remove:
                self._bot.api.remove_user_note(itx.user.id, rec_id)

            # Send link to new playlist
            desc = '\n'.join([
                "https://open.spotify.com/playlist/{}".format(playlist_id),
                "Added to your Spotify library"
            ])
            embed = Embed(
                title='Playlist created',
                description=f'{len(tracks)} tracks moved from your list to Spotify',
                color=Color.green()
            )
            embed.add_field(name=playlist_name, value=desc)
            embed.set_thumbnail(url=icon)
            await itx.followup.send(embed=embed)
        else:
            await itx.followup.send(embed=create_error_embed(
                body='None of your recommendations are Spotify tracks.'
            ))
