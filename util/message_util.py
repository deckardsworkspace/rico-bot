from nextcord.ext.commands import Context
from typing import List, Union


async def remove_multiple_messages(ctx: Context, ids: List[Union[str, int]]):
    for msg_id in ids:
        try:
            msg = await ctx.fetch_message(int(msg_id) if isinstance(msg_id, str) else msg_id)
            await msg.delete()
        except Exception as e:
            print("Error while trying to remove message: {}".format(e))
