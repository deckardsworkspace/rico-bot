from nextcord import ButtonStyle, Interaction
from nextcord.ext.commands import Context
from nextcord.ui import button, Button, View


class NowPlayingView(View):
    def __init__(self, ctx: Context):
        super().__init__()
        self.ctx = ctx
    
    @button(label='📃', style=ButtonStyle.grey)
    async def show_queue(self, _: Button, interaction: Interaction):
        pass
    
    @button(label='⏮️', style=ButtonStyle.grey)
    async def skip_backward(self, _: Button, interaction: Interaction):
        pass

    @button(label='⏯️', style=ButtonStyle.blurple)
    async def toggle_pause(self, _: Button, interaction: Interaction):
        pass

    @button(label='⏭️', style=ButtonStyle.grey)
    async def skip_forward(self, _: Button, interaction: Interaction):
        pass
    
    @button(label='⏹️', style=ButtonStyle.red)
    async def stop(self, _: Button, interaction: Interaction):
        pass
