from lavalink.models import BasePlayer
from nextcord import Color
from nextcord.ext.commands import Context
from pyrebase.pyrebase import Database
from util import MusicEmbed
from .queue_helpers import enqueue, dequeue_db, set_queue_index


async def send_loop_embed(ctx: Context):
    embed = MusicEmbed(
        color=Color.dark_green(),
        title=f':repeat:｜Looping back to the start',
        description=[
            'Reached the end of the queue.',
            f'Use the `loop all` command to disable.'
        ]
    )
    await embed.send(ctx)


async def try_enqueue(ctx: Context, db: Database, player: BasePlayer, track_index: int, queue_end: bool) -> bool:
    track = dequeue_db(db, str(ctx.guild.id), track_index)
    try:
        if await enqueue(ctx.bot, track, ctx=ctx):
            if not queue_end:
                await player.skip()

            # Save new queue index back to db
            set_queue_index(db, str(ctx.guild.id), track_index)
            return True
    except Exception as e:
        embed = MusicEmbed(
            color=Color.red(),
            title=f':x:｜Unable to play track',
            description=[
                f'Track: `{track}`'
                f'Reason: `{e}`'
            ]
        )
        await embed.send(ctx)
    return False
