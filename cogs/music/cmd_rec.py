from nextcord import Color
from nextcord.ext.commands import command, Context
from util import sanitize_youtube_name, RicoEmbed


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
        track_info = player.fetch(current_id)
        if track_info and 'title' in track_info:
            if 'spotify' in track_info:
                track_id = track_info['spotify']['id']
                return await ctx.invoke(cmd, f'spotify:track:{track_id}')
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
