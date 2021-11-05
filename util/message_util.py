from dataclasses import dataclass, field
from nextcord import Color, Embed, Message
from nextcord.ext.commands import Context
from typing import List, Union


@dataclass
class MusicEmbed:
    # All optional
    title: str = Embed.Empty
    color: Color = Color.og_blurple()
    description: Union[str, List[str]] = Embed.Empty
    fields: List[List[str]] = field(default_factory=list)
    inline_fields: bool = False
    thumbnail_url: str = Embed.Empty
    image_url: str = Embed.Empty

    # Header and footer
    header: str = Embed.Empty
    header_url: str = Embed.Empty
    header_icon_url: str = Embed.Empty
    footer: str = Embed.Empty
    footer_icon_url: str = Embed.Empty

    # Create embed
    def __post_init__(self):
        # Can't specify header/footer icons without header/footer names
        if self.header is Embed.Empty and self.header_icon_url is not Embed.Empty:
            raise ValueError("Can't specify header icon without header text.")
        if self.footer is Embed.Empty and self.footer_icon_url is not Embed.Empty:
            raise ValueError("Can't specify footer icon without footer text.")

        # Create embed object
        description = self.description
        if isinstance(self.description, list):
            description = '\n'.join(self.description)
        embed = Embed(title=self.title, description=description, color=self.color)
        
        # Set embed parts
        if self.header is not Embed.Empty:
            embed.set_author(name=self.header)
        if self.thumbnail_url is not Embed.Empty:
            embed.set_thumbnail(url=self.thumbnail_url)
        if self.image_url is not Embed.Empty:
            embed.set_image(url=self.image_url)
        if self.header is not Embed.Empty:
            embed.set_author(name=self.header, url=self.header_url, icon_url=self.header_icon_url)
        if self.footer is not Embed.Empty:
            embed.set_footer(text=self.footer, icon_url=self.footer_icon_url)
        if len(self.fields):
            for field in self.fields:
                embed.add_field(name=field[0], value=field[1], inline=self.inline_fields)

        # Save embed
        self.embed = embed
    
    # Get embed object
    def get(self) -> Embed:
        return self.embed
        
    # Send embed
    async def send(self, ctx: Context, as_reply: bool = False) -> Message:
        if as_reply:
            return await ctx.reply(embed=self.embed)
        return await ctx.send(embed=self.embed)


async def remove_multiple_messages(ctx: Context, ids: List[Union[str, int]]):
    for msg_id in ids:
        try:
            msg = await ctx.fetch_message(int(msg_id) if isinstance(msg_id, str) else msg_id)
            await msg.delete()
        except Exception as e:
            print("Error while trying to remove message: {}".format(e))
