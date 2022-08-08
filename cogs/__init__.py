from typing import TYPE_CHECKING
from .export import ExportCog
from .notes import NotesCog
from .thread import ThreadsCog
if TYPE_CHECKING:
    from util.rico_bot import RicoBot


def setup(bot: 'RicoBot'):
    # Add cogs
    bot.add_cog(ExportCog(bot))
    bot.add_cog(NotesCog(bot))
    bot.add_cog(ThreadsCog(bot))

    # Sync slash commands
    bot.loop.create_task(bot.sync_all_application_commands())
