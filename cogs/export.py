import base64
import json
import requests.exceptions
from nextcord import Embed
from nextcord.ext import commands
from ratelimit import RateLimitException


class Export(commands.Cog):
    def __init__(self, client, db, spotify):
        self.client = client
        self.db = db
        self.spotify = spotify

    async def __cancel_auth(self, ctx, message):
        await ctx.reply(message)
        self.db.child("spotify_auth").child(str(ctx.author.id)).remove()

    @commands.command(name="auth", aliases=["login"])
    async def authenticate(self, ctx):
        """
        Authenticate Rico with your Spotify account, so you can export your recommended songs.
        """
        # Check if already authenticated
        auth_data = self.db.child("spotify_auth").child(str(ctx.author.id)).get().val()
        if auth_data and "refresh_token" in auth_data:
            await ctx.reply("You're already authenticated with Spotify! To deauthenticate, DM me `rc!deauth`.")
            return

        # Create auth URL
        auth_url, verifier, state = self.spotify.create_auth_url()

        # Store verifier and state in DB for later
        self.db.child("spotify_auth").child(str(ctx.author.id)).set({
            "verifier": verifier,
            "state": state
        })

        # Send direct message to user
        msg = '\n\n'.join([
            "Hi! To begin exporting your Spotify recommendations,",
            "1. Open {} in your browser to authenticate with Spotify.".format(auth_url),
            "2. You'll be given a random token. Send it here and you're done!"
        ])
        await ctx.author.send(msg)
        await ctx.reply('Sent you a DM!')

    @commands.dm_only()
    @commands.command(name="deauth", aliases=["logout"])
    async def deauthenticate(self, ctx):
        """
        Permanently remove your Spotify account authentication data from Rico's database.
        """
        await self.__cancel_auth(ctx, "Removed Spotify authentication data.")

    @commands.dm_only()
    @commands.command(name="finishauth", aliases=["fa"])
    async def get_token(self, ctx, token):
        """
        Finish Spotify authentication using a Spotify-provided authentication code.
        """
        # Get verifier and state
        auth_data = self.db.child("spotify_auth").child(str(ctx.author.id)).get().val()
        if "verifier" not in auth_data or "state" not in auth_data:
            await self.__cancel_auth(ctx, "Invalid or no authentication data found. Maybe try `rc!auth` again?")
            return
        verifier = auth_data['verifier']
        state = auth_data['state']

        # Decode token
        auth_result = json.loads(base64.b64decode(token))
        if auth_result['state'] != state:
            await self.__cancel_auth(ctx, "State mismatch. Please try authenticating again.")
            return
        if "error" in auth_result:
            cause = auth_result['error']
            if cause == "access_denied":
                await self.__cancel_auth(ctx, "You denied access to your Spotify playlists :pensive:")
            else:
                await self.__cancel_auth(ctx, "Error while authenticating: {}. Please try again.".format(cause))
            return

        # Exchange auth code with access token
        try:
            auth_tokens = self.spotify.request_token(code=auth_result['code'], verifier=verifier)
        except requests.exceptions.HTTPError:
            await self.__cancel_auth(ctx, "Error while requesting access from Spotify. Please try again.")
            return

        # Store tokens
        access_token, expires_in, refresh_token = auth_tokens
        self.db.child("spotify_auth").child(str(ctx.author.id)).set({
            "access_token": access_token,
            "expires_in": expires_in,
            "refresh_token": refresh_token
        })
        await ctx.author.send("Authenticated! :sparkles: You may now use the `rc!dump` command to export tracks.")

    @commands.command(name="dump")
    async def dump_spotify(self, ctx):
        """
        Export all your recommended Spotify tracks to a new Spotify playlist.
        Requires authentication with Spotify first (rc!startauth).
        """
        # Get auth data
        token_data = self.db.child("spotify_auth").child(str(ctx.author.id)).get().val()

        # Exit if not authenticated
        if not token_data or "access_token" not in token_data:
            await ctx.reply("You aren't authenticated with Spotify yet. Try `rc!auth`.")

        # Get all Spotify tracks recommended to user
        recs = self.db.child("recommendations").child("user").child(str(ctx.author.id)).get().val()
        tracks = []
        to_remove = []
        for index, item in recs.items():
            if "id" in item and item['type'] == "spotify-track":
                tracks.append("spotify:track:{}".format(item['id']))
                to_remove.append(index)

        # Add to playlist
        if len(tracks):
            try:
                result = self.spotify.create_playlist(token_data, ctx.author.name, tracks)
                access_token, expires_in, refresh_token, playlist_name, playlist_id = result
            except requests.exceptions.HTTPError as e:
                await ctx.reply("Error communicating with Spotify: `{}`. Please try again later.".format(e))
                return
            except RateLimitException:
                await ctx.reply(":stop_sign: You are being rate-limited. Please try again later.")
                return

            # Store new access tokens
            if access_token != token_data['access_token']:
                self.db.child("spotify_auth").child(str(ctx.author.id)).set({
                    "access_token": access_token,
                    "expires_in": expires_in,
                    "refresh_token": refresh_token
                })

            # Get playlist art
            icon = self.spotify.get_playlist_cover(playlist_id, default=ctx.author.avatar.url)

            # Link to new playlist
            desc = '\n'.join([
                "https://open.spotify.com/playlist/{}".format(playlist_id),
                "Added to your Spotify library"
            ])
            embed = Embed(title="Playlist created",
                          description="{} tracks moved from your list to Spotify".format(len(tracks)),
                          color=0x20ce09)
            embed.add_field(name=playlist_name, value=desc)
            embed.set_thumbnail(url=icon)
            await ctx.reply(embed=embed)

            # Delete tracks from rec list
            for item in to_remove:
                self.db.child("recommendations").child("user").child(str(ctx.author.id)).child(item).remove()
        else:
            await ctx.reply("None of your recommendations are Spotify tracks, sorry :pensive:")
