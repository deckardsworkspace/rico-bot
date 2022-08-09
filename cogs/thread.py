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
        self._bot.api.update_guild(itx.guild_id, itx.guild.name)

    @tasks.loop(seconds=3600)
    async def main(self):
        """
        Keep threads unarchived for monitored guilds. Run every hour.
        """
        if not self._bot.is_closed():
            for guild in self._bot.guilds:
                if guild.id in self._bot.api.get_thread_managed_guilds():
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
        if guild_id not in self._bot.api.get_thread_managed_guilds():
            # Guild is not monitored. Do nothing.
            return

        if thread.id not in self._bot.api.get_excluded_threads(guild_id) and thread.archived:
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
        if thread.id in self._bot.api.get_excluded_threads(thread.guild.id):
            self._bot.api.remove_excluded_thread(thread.guild.id, thread.id)

    @Cog.listener()
    async def on_thread_update(self, before: Thread, after: Thread):
        if not before.archived and after.archived:
            # Thread was archived, unarchive if not excluded
            if self._bot.debug:
                print(f'[DEBUG] Unarchiving thread {after.id} in guild {after.guild.id}')
            return await self.unarchive_thread(after.guild.id, after)

    @slash_command(name='managethread', guild_ids=get_debug_guilds())
    @application_checks.check(is_in_thread)
    @application_checks.has_guild_permissions(administrator=True)
    async def manage_thread(self, itx: Interaction):
        """
        Exclude this thread from being automatically unarchived.
        """
        await itx.response.defer()

        # Check if we're monitoring this guild
        if not self._bot.api.get_thread_manage_status(itx.guild_id):
            return await itx.followup.send(embed=create_error_embed(
                title='Can\'t use this command',
                body='Threads aren\'t being managed in this server. Enable with `/enablemanage`.'
            ))

        # Check if thread is not in excluded list
        if not self._bot.api.check_excluded_thread(itx.guild_id, itx.channel_id):
            return await itx.followup.send(embed=create_error_embed(
                body=f'Thread **{itx.channel.name}** is already being managed.'
            ))

        # Remove from excluded list
        self._bot.api.remove_excluded_thread(itx.guild_id, itx.channel_id)
        return await itx.followup.send(embed=create_success_embed(
            body=f'Thread **{itx.channel.name}** is now being managed.'
        ))

    @slash_command(name='unmanagethread', guild_ids=get_debug_guilds())
    @application_checks.check(is_in_thread)
    @application_checks.has_guild_permissions(administrator=True)
    async def unmanage_thread(self, itx: Interaction):
        """
        Allow this thread to be automatically archived after becoming inactive.
        """
        await itx.response.defer()

        # Check if we're monitoring this guild
        if not self._bot.api.get_thread_manage_status(itx.guild_id):
            return await itx.followup.send(embed=create_error_embed(
                title='Can\'t use this command',
                body='Threads aren\'t being managed in this server. Enable with `/enablemanage`.'
            ))

        # Check if thread is not excluded
        if self._bot.api.check_excluded_thread(itx.guild_id, itx.channel_id):
            return await itx.followup.send(embed=create_error_embed(
                body=f'Thread **{itx.channel.name}** is not being managed.'
            ))

        # Add to excluded list
        self._bot.api.add_excluded_thread(itx.guild_id, itx.channel_id)

        # Offer the user the option to archive the thread now
        archive_duration = min_to_dh(itx.channel.auto_archive_duration)
        archival_msg = f'Thread **{itx.channel.name}** will be archived after {archive_duration}'
        message = await itx.followup.send(embed=create_success_embed(
            title='No longer managing thread',
            body='\n'.join([
                archival_msg,
                'To archive this thread now, react 🗑️ below.'
            ])
        ))
        embed = message.embeds[0]
        await message.add_reaction('🗑️')

        # Wait for user to react
        def check(reaction: Reaction, user: User | Member):
            return user.id == itx.user.id and str(reaction.emoji) == '🗑️'
        archive_now = False
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

    @slash_command(name='enablemanage', guild_ids=get_debug_guilds())
    @application_checks.has_guild_permissions(administrator=True)
    async def enable_thread_management(self, itx: Interaction):
        """
        Enable automatic unarchiving of threads in this server.
        """
        await itx.response.defer()

        # Check monitoring status
        if self._bot.api.get_thread_manage_status(itx.guild_id):
            # Already monitoring guild
            return await itx.followup.send(embed=create_error_embed(
                body=f'Thread management is already enabled for **{itx.guild.name}**'
            ))

        # Enable thread management
        self._bot.api.set_thread_manage_status(itx.guild_id, True)
        await itx.followup.send(embed=create_success_embed(
            body=f'Thread management enabled for **{itx.guild.name}**\nInactive threads will be kept unarchived.'
        ))

        # Immediately unarchive threads
        await self.unarchive_threads_guild(itx.guild)

    @slash_command(name='disablemanage', guild_ids=get_debug_guilds())
    @application_checks.has_guild_permissions(administrator=True)
    async def disable_thread_management(self, itx: Interaction):
        """
        Disable automatic unarchiving of threads in this server.
        """
        await itx.response.defer()

        # Check monitoring status
        if not self._bot.api.get_thread_manage_status(itx.guild_id):
            # Already monitoring guild
            return await itx.followup.send(embed=create_error_embed(
                body=f'Thread management is already disabled for **{itx.guild.name}**'
            ))

        # Enable thread management
        self._bot.api.set_thread_manage_status(itx.guild_id, False)
        await itx.followup.send(embed=create_success_embed(
            body=f'Thread management disabled for **{itx.guild.name}**\nInactive threads will be auto-archived.'
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
            body='Unarchived all managed threads in all monitored servers'
        ))

    @slash_command(name='unarchiveall', guild_ids=get_debug_guilds())
    @application_checks.has_guild_permissions(administrator=True)
    async def unarchive_guild(self, itx: Interaction):
        """
        Unarchive all unexcluded threads in this guild
        """
        await itx.response.defer(ephemeral=True)
        if not self._bot.api.get_thread_manage_status(itx.guild_id):
            return await itx.followup.send(embed=create_error_embed(
                title='Can\'t use this command',
                body='Threads aren\'t being managed in this server. Enable with `/enablemanage`.'
            ))

        await self.unarchive_threads_guild(itx.guild)
        return await itx.followup.send(embed=create_success_embed(body='Unarchived all managed threads in this server'))
