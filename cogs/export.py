from dataclass.custom_embed import create_error_embed, create_success_embed
from nextcord import Color, Embed, Interaction, slash_command
from nextcord.ext.commands import Cog
from ratelimit import RateLimitException
import requests.exceptions
from typing import TYPE_CHECKING
from util.config import get_debug_guilds
from util.enums import RecommendationType
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

    async def _cancel_auth(self, itx: Interaction, message: str):
        # Remove user data from auth table
        self._bot.db.remove_user_spotify_creds(itx.user.id)

        # Send error message
        embed = create_error_embed(
            title='Logged out from Spotify',
            body=message
        )
        if itx.response.is_done():
            await itx.followup.send(embed=embed)
        else:
            await itx.response.send_message(embed=embed)

    @slash_command(name='spotifylogin', guild_ids=get_debug_guilds())
    async def authenticate(self, itx: Interaction):
        """
        Authenticate Rico with your Spotify account, so you can export your recommended songs.
        """
        await itx.response.defer(ephemeral=True)

        # Check if already authenticated
        try:
            _ = self._bot.db.get_user_spotify_creds(itx.user.id)
        except RuntimeError:
            pass
        else:
            return await itx.followup.send(embed=create_success_embed(
                title='Already authenticated',
                body=f'You can use the `/spotifyexport` command to export your Spotify recommendations, '
                     f'or `/spotifylogout` to log out of Spotify. '
            ))

        # Create auth URL
        auth_url, verifier, state = self.spotify.create_auth_url()

        # Store verifier and state in DB for later
        self._bot.db.set_user_spotify_pkce(itx.user.id, verifier, state)

        # Send auth URL to user
        await itx.followup.send(embed=create_success_embed(
            title='Login URL generated',
            body=f'Please open the following URL in your browser to login with Spotify:\n{auth_url}'
        ))

    @slash_command(name='spotifylogout', guild_ids=get_debug_guilds())
    async def deauthenticate(self, itx: Interaction):
        """
        Permanently remove your Spotify account authentication data from Rico's database.
        """
        await self._cancel_auth(itx, 'Removed Spotify authentication data.')

    @slash_command(name='spotifyexport', guild_ids=get_debug_guilds())
    async def dump_spotify(self, itx: Interaction):
        """
        Export all your recommended Spotify tracks to a new Spotify playlist.
        Requires authentication with Spotify first (`/spotifylogin`).
        """
        await itx.response.defer(ephemeral=True)

        # Get auth data
        try:
            credentials = self._bot.db.get_user_spotify_creds(itx.user.id)
        except RuntimeError:
            return await itx.followup.send(embed=create_error_embed(
                title='Not authenticated',
                body='You need to authenticate with Spotify first (`/spotifylogin`).'
            ))

        # Get all Spotify tracks recommended to user
        recs = self._bot.db.get_user_recommendations(itx.user.id)
        tracks = []
        to_remove = []
        for item in recs:
            if item.type == RecommendationType.SPOTIFY_TRACK:
                _, track_id = parse_spotify_url(item.url)
                tracks.append(f'spotify:track:{track_id}')
                to_remove.append(item.id)

        # Add to playlist
        if len(tracks):
            try:
                result = self.spotify.create_playlist(credentials, itx.user.name, tracks)
                credentials, playlist_name, playlist_id = result
            except requests.exceptions.HTTPError as e:
                return await itx.followup.send(embed=create_error_embed(
                    title='Error communicating with Spotify',
                    body=f'`{e}`\nPlease try again later.'
                ))
            except RateLimitException:
                return await itx.followup.send(embed=create_error_embed(
                    title='Rate limit exceeded',
                    body='Please try again later.'
                ))

            # Store new access token
            self._bot.db.set_user_spotify_creds(itx.user.id, credentials)

            # Get playlist art
            icon = self.spotify.get_playlist_cover(playlist_id, default=itx.user.avatar.url)

            # Delete tracks from rec list
            for rec_id in to_remove:
                self._bot.db.remove_user_recommendation(itx.user.id, rec_id)

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
