from lavalink.models import BasePlayer
from nextcord import ButtonStyle, Interaction
from nextcord.ext.commands import Context
from nextcord.ui import button, Button, View


class NowPlayingView(View):
    def __init__(self, ctx: Context, player: BasePlayer):
        super().__init__()
        self.ctx = ctx
        self.player = player
    
    @button(label='📃', style=ButtonStyle.grey)
    async def show_queue(self, _: Button, interaction: Interaction):
        pass
    
    @button(label='⏮️', style=ButtonStyle.grey)
    async def skip_backward(self, _: Button, interaction: Interaction):
        cmd = self.ctx.bot.get_command('previous')
        return await self.ctx.invoke(cmd)

    @button(label='⏯️', style=ButtonStyle.blurple)
    async def toggle_pause(self, _: Button, interaction: Interaction):
        if self.player.paused:
            cmd = self.ctx.bot.get_command('unpause')
        else:
            cmd = self.ctx.bot.get_command('pause')
        return await self.ctx.invoke(cmd)

    @button(label='⏭️', style=ButtonStyle.grey)
    async def skip_forward(self, _: Button, interaction: Interaction):
        cmd = self.ctx.bot.get_command('skip')
        return await self.ctx.invoke(cmd)
    
    @button(label='⏹️', style=ButtonStyle.red)
    async def stop(self, _: Button, interaction: Interaction):
        pass
