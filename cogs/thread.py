from asyncio import CancelledError, TimeoutError
from dataclass.custom_embed import create_error_embed, create_success_embed, CustomEmbed
from nextcord import ApplicationError, Color, Guild, Interaction, Member, Reaction, slash_command, Thread, User
from nextcord.ext import application_checks, tasks
from nextcord.ext.commands import Cog
from ratelimit import limits, sleep_and_retry
from typing import TYPE_CHECKING
from util.config import get_debug_guilds
from util.string_util import min_to_dh
if TYPE_CHECKING:
    from util.rico_bot import RicoBot


def is_in_thread(itx: Interaction) -> bool:
    """
    Check if the command is being invoked from within a thread
    """
    result = isinstance(itx.channel, Thread)
    if not result:
        raise ApplicationError('This command can only be used from within a thread.')
    return result


class ThreadsCog(Cog):
    def __init__(self, bot: 'RicoBot'):
        self._bot = bot
        self.main.start()
        print(f'Loaded cog: {self.__class__.__name__}')
    
    async def cog_application_command_before_invoke(self, itx: Interaction):
        """
        Ensure that the guild exists in the database before processing any commands
        """
        self._bot.db.update_guild(itx.guild_id, itx.guild.name)

    @tasks.loop(seconds=3600)
    async def main(self):
        """
        Keep threads unarchived for monitored guilds. Run every hour.
        """
        if not self._bot.is_closed():
            for guild in self._bot.guilds:
                if guild.id in self._bot.db.get_thread_managed_guilds():
                    await self.unarchive_threads_guild(guild)

    @main.before_loop
    async def before_main(self):
        """
        Wait until client is ready before housekeeping
        """
        await self._bot.wait_until_ready()

    @sleep_and_retry
    @limits(calls=15, period=5)
    async def unarchive_thread(self, guild_id: int, thread: Thread):
        """
        Unarchive a thread if not excluded from monitoring
        """
        # Check if guild is monitored
        if guild_id not in self._bot.db.get_thread_managed_guilds():
            # Guild is not monitored. Do nothing.
            return

        if thread.id not in self._bot.db.get_excluded_threads(guild_id) and thread.archived:
            await thread.edit(archived=False)

    async def unarchive_threads_guild(self, guild: Guild):
        """
        Unarchive all non-excluded threads in a guild
        """
        for thread in guild.threads:
            await self.unarchive_thread(guild.id, thread)
    
    @Cog.listener()
    async def on_thread_delete(self, thread: Thread):
        """
        Remove deleted thread from DB
        """
        if thread.id in self._bot.db.get_excluded_threads(thread.guild.id):
            self._bot.db.remove_excluded_thread(thread.guild.id, thread.id)

    @Cog.listener()
    async def on_thread_update(self, before: Thread, after: Thread):
        if not before.archived and after.archived:
            # Thread was archived, unarchive if not excluded
            return await self.unarchive_thread(after.guild.id, after)

    @slash_command(name='toggleexclusion', guild_ids=get_debug_guilds())
    @application_checks.check(is_in_thread)
    @application_checks.has_guild_permissions(administrator=True)
    async def toggle_exclusion(self, itx: Interaction):
        """
        Exclude or include this thread from being automatically unarchived.
        """
        await itx.response.defer()

        # Check if we're monitoring this guild
        if not self._bot.db.get_thread_manage_status(itx.guild_id):
            return await itx.followup.send(embed=create_error_embed(
                title='Can\'t use this command',
                body='This guild is not being monitored for archived threads. Use `/togglemonitoring` to enable.'
            ))

        # Check if thread is already excluded
        if self._bot.db.check_excluded_thread(itx.guild_id, itx.channel_id):
            # Already in exclude list. Remove from list.
            self._bot.db.remove_excluded_thread(itx.guild_id, itx.channel_id)
            await itx.followup.send(embed=create_success_embed(body=f'Thread **{itx.channel.name}** will now be automatically unarchived.'))
        else:
            # Not in exclude list. Add to list.
            self._bot.db.add_excluded_thread(itx.guild_id, itx.channel_id)
        
            # Offer the user the option to archive the thread now
            archive_duration = min_to_dh(itx.channel.auto_archive_duration)
            archival_msg = f'Thread **{itx.channel.name}** will be archived after {archive_duration}'
            embed = CustomEmbed(
                color=Color.green(),
                title=':white_check_mark:｜Excluded thread from persistence',
                description=[
                    archival_msg,
                    'To archive this thread now, react 🗑️ below.'
                ]
            )
            message = await itx.followup.send(embed=embed.get())
            embed = message.embeds[0]
            await message.add_reaction('🗑️')

            # Wait for user to react
            archive_now = False
            def check(r: Reaction, u: User | Member):
                return u.id == itx.user.id and str(r.emoji) == '🗑️'
            try:
                r, u = await self._bot.wait_for('reaction_add', check=check, timeout=60.0)
            except (CancelledError, TimeoutError) as _:
                # Remove prompt from message
                embed.description = archival_msg
            else:
                # Archive the thread now
                embed.description = f'Thread **{itx.channel.name}** is now archived'
                archive_now = True
            finally:
                # Remove all reactions to the message
                await message.clear_reactions()
                await message.edit(embed=embed)
                if archive_now:
                    await itx.channel.edit(archived=True)

    @slash_command(name='togglemonitoring', guild_ids=get_debug_guilds())
    @application_checks.has_guild_permissions(administrator=True)
    async def toggle_monitoring(self, itx: Interaction):
        """
        Enable or disable automatic unarchiving of threads in this server.
        """
        await itx.response.defer()

        # Check monitoring status
        if self._bot.db.get_thread_manage_status(itx.guild_id):
            # Already monitoring guild. Disable.
            self._bot.db.set_thread_manage_status(itx.guild_id, False)
            await itx.channel.send(embed=create_success_embed(
                body=f'Thread monitoring disabled for {itx.guild.name}. All threads will be automatically archived as normal.'
            ))
        else:
            # Not monitoring guild. Enable.
            self._bot.db.set_thread_manage_status(itx.guild_id, True)

            # Immediately unarchive threads
            await self.unarchive_threads_guild(itx.guild)
            await itx.followup.send(embed=create_success_embed(
                body=f'Thread monitoring enabled for {itx.guild.name}. Threads will be kept unarchived.'
            ))
    
    @slash_command(name='unarchiveglobal', guild_ids=get_debug_guilds())
    @application_checks.is_owner()
    async def unarchive_all(self, itx: Interaction):
        """
        Unarchive all threads in all monitored guilds
        """
        await itx.response.defer(ephemeral=True)
        for guild in self._bot.guilds:
            await self.unarchive_threads_guild(guild)
        return await itx.followup.send(embed=create_success_embed(
            body='Unarchived all unexcluded threads in all monitored servers'
        ))

    @slash_command(name='unarchive', guild_ids=get_debug_guilds())
    @application_checks.has_guild_permissions(administrator=True)
    async def unarchive_guild(self, itx: Interaction):
        """
        Unarchive all unexcluded threads in this guild
        """
        await itx.response.defer(ephemeral=True)
        if not self._bot.db.get_thread_manage_status(itx.guild_id):
            return await itx.followup.send(embed=create_error_embed(
                body='Thread unarchiving is not enabled on this server. Enable it using the `ttm` command.')
            )

        await self.unarchive_threads_guild(itx.guild)
        return await itx.followup.send(embed=create_success_embed(body='Unarchived all unexcluded threads in this server'))
