from lavalink.models import BasePlayer
from nextcord import ButtonStyle, Interaction
from nextcord.ext.commands import Context
from nextcord.ui import button, Button, View


class NowPlayingView(View):
    def __init__(self, ctx: Context, player: BasePlayer):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.player = player
    
    @button(label='Queue', style=ButtonStyle.grey)
    async def show_queue(self, _: Button, interaction: Interaction):
        cmd = self.ctx.bot.get_command('queue')
        embed = await self.ctx.invoke(cmd, is_interaction=True)
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @button(label='Prev', style=ButtonStyle.grey)
    async def skip_backward(self, _: Button, interaction: Interaction):
        cmd = self.ctx.bot.get_command('previous')
        return await self.ctx.invoke(cmd, is_interaction=True)

    @button(label='Play/Pause', style=ButtonStyle.blurple)
    async def toggle_pause(self, _: Button, interaction: Interaction):
        if self.player.paused:
            cmd = self.ctx.bot.get_command('unpause')
        else:
            cmd = self.ctx.bot.get_command('pause')
        return await self.ctx.invoke(cmd, is_interaction=True)

    @button(label='Next', style=ButtonStyle.grey)
    async def skip_forward(self, _: Button, interaction: Interaction):
        cmd = self.ctx.bot.get_command('skip')
        return await self.ctx.invoke(cmd, is_interaction=True)
    
    @button(label='Stop', style=ButtonStyle.red)
    async def stop(self, _: Button, interaction: Interaction):
        cmd = self.ctx.bot.get_command('stop')
        return await self.ctx.invoke(cmd)
