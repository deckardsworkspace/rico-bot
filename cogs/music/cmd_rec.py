from nextcord.ext.commands import command, Context
from util import sanitize_youtube_name


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
            return await ctx.reply('Error: Invalid now playing info.')
    else:
        return await ctx.reply('Nothing is playing right now!')
