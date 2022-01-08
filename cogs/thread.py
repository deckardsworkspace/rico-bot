from math import floor
from nextcord import Color, Guild, Member, Message, Reaction, Thread
from nextcord.ext import tasks
from nextcord.ext.commands import Bot, Cog, command, Context, is_owner
from pyrebase.pyrebase import Database
from typing import List, Union
from util import RicoEmbed


def min_to_dh(mins: int) -> str:
    days = floor(mins / 1440)
    extra_min = mins % 1440
    hours = floor(extra_min / 60)
    days_plural = 's' if days > 1 else ''
    hours_plural = 's' if hours > 1 else ''

    if days > 0:
        if hours > 0:
            return f'{days:01d} day{days_plural}, {hours:02d} hour{hours_plural}'
        return f'{days:01d} day{days_plural}'
    return f'{hours:02d} hour{hours_plural}'


async def send_error_embed(ctx: Context, message: Union[str, List[str]]) -> Message:
    embed = RicoEmbed(
        color=Color.red(),
        title=':x:｜Error',
        description=message
    )
    return await embed.send(ctx, as_reply=True)


async def send_success_embed(ctx: Context, message: Union[str, List[str]]) -> Message:
    embed = RicoEmbed(
        color=Color.green(),
        title=':white_check_mark:｜Success',
        description=message
    )
    return await embed.send(ctx, as_reply=True)


class ThreadManager(Cog):
    def __init__(self, bot: Bot, db: Database):
        self.bot = bot
        self.db = db
        self.main.start()
        print('Loaded cog: ThreadManager')
    
    def is_monitored(self, guild_id: str) -> bool:
        """Check if a guild is monitored"""
        monitored_guilds = self.db.child('thread_manager').child('monitored').get().val()
        if monitored_guilds is None or guild_id not in monitored_guilds.keys() or not monitored_guilds[guild_id]:
            return False
        return True

    @tasks.loop(seconds=3600)
    async def main(self):
        """Run housekeeping every hour"""
        if not self.bot.is_closed():
            await self.unarchive_threads()

    @main.before_loop
    async def before_main(self):
        """Wait until client is ready before housekeeping."""
        await self.bot.wait_until_ready()
    
    @is_owner()
    @command(name='uaa')
    async def unarchive_all(self, ctx: Context):
        """Unarchive all threads in all monitored guilds"""
        for guild in self.bot.guilds:
            await self.unarchive_threads_guild(guild)
        return await send_success_embed(ctx, 'Unarchived all unexcluded threads in all monitored servers')

    @command(name='ua')
    async def unarchive_guild(self, ctx: Context):
        """Unarchive all unexcluded threads in this guild"""
        if not ctx.author.guild_permissions.administrator:
            return await send_error_embed(ctx, 'This command can only be used by an administrator.')
        if not self.is_monitored(str(ctx.guild.id)):
            return await send_error_embed(ctx, 'Thread unarchiving is not enabled on this server. Enable it using the `ttm` command.')

        await self.unarchive_threads_guild(ctx.guild)
        return await send_success_embed(ctx, 'Unarchived all unexcluded threads in this server')

    async def unarchive_thread(self, guild_id: str, thread: Thread):
        """Unarchive a thread if not excluded from monitoring."""
        thread_id = str(thread.id)
        
        # Check if guild is monitored
        if not self.is_monitored(guild_id):
            # Guild is not monitored. Do nothing.
            return

        # Get list of excluded thread IDs
        excluded_threads = self.db.child('thread_manager').child('exclude').child(guild_id).get().val()
        if excluded_threads is None or thread_id not in excluded_threads.keys() or not excluded_threads[thread_id]:
            # Unarchive thread if not excluded from monitoring
            if thread.archived:
                await thread.edit(archived=False)
    
    async def unarchive_threads(self):
        """Keep threads unarchived for monitored guilds"""

        # Get list of monitored guilds
        monitored_guilds = self.db.child('thread_manager').child('monitored').get().val()
        if monitored_guilds is not None and len(monitored_guilds.keys()):
            guild_ids = [int(x) for x in monitored_guilds.keys()]

            for guild in self.bot.guilds:
                if guild.id in guild_ids:
                    await self.unarchive_threads_guild(guild)
    
    async def unarchive_threads_guild(self, guild: Guild):
        """Unarchive all threads in a guild if not excluded"""

        for thread in guild.threads:
            # Unarchive if not excluded
            await self.unarchive_thread(str(guild.id), thread)
    
    @Cog.listener()
    async def on_thread_delete(self, thread: Thread):
        """Remove deleted thread from DB"""
        
        # Get list of excluded thread IDs
        excluded_threads = self.db.child('thread_manager').child('exclude').child(str(thread.guild.id)).get().val()
        if excluded_threads is not None and str(thread.id) in excluded_threads.keys():
            self.db.child('thread_manager').child('exclude').child(str(thread.guild.id)).child(str(thread.id)).remove()
    
    @Cog.listener()
    async def on_thread_update(self, before: Thread, after: Thread):
        if not before.archived and after.archived:
            # Thread was archived, unarchive if not excluded
            return await self.unarchive_thread(str(after.guild.id), after)

    @command(name='tte')
    async def toggle_exclusion(self, ctx: Context):
        if not ctx.author.guild_permissions.administrator:
            return await send_error_embed(ctx, 'This command can only be used by an administrator.')
        if not isinstance(ctx.channel, Thread):
            return await send_error_embed(ctx, 'This command can only be used in a thread.')

        # Get list of excluded thread IDs
        invoked_thread = str(ctx.channel.id)
        excluded_threads = self.db.child('thread_manager').child('exclude').child(str(ctx.guild.id)).get().val()
        if excluded_threads is not None and invoked_thread in excluded_threads:
            # Already in exclude list
            new_state = not excluded_threads[invoked_thread]
        else:
            # Not in exclude list
            new_state = True
        
        self.db.child('thread_manager').child('exclude').child(str(ctx.guild.id)).update({f'{invoked_thread}': new_state})
        if not new_state:
            return await send_success_embed(ctx, f'Thread **{ctx.channel.name}** will be kept unarchived')
        
        # If thread is now set to auto archive,
        # offer the user the option to archive the thread now
        archive_duration = min_to_dh(ctx.channel.auto_archive_duration)
        archival_msg = f'Thread **{ctx.channel.name}** will be archived after {archive_duration}'
        embed = RicoEmbed(
            color=Color.green(),
            title=':white_check_mark:｜Excluded thread from persistence',
            description=[
                archival_msg,
                'To archive this thread now, react 🗑️ below.'
            ]
        )
        message = await embed.send(ctx, as_reply=True)
        embed = message.embeds[0]
        await message.add_reaction('🗑️')

        # Wait for user to react
        archive_now = False
        def check(r: Reaction, u: Member):
            return u == ctx.author and str(r.emoji) == '🗑️'
        try:
            r, u = await ctx.bot.wait_for('reaction_add', check=check, timeout=60.0)
        except TimeoutError:
            # Remove prompt from message
            embed.description = archival_msg
        else:
            # Archive the thread now
            embed.description = f'Thread **{ctx.channel.name}** is now archived'
            archive_now = True
        finally:
            # Remove all reactions to the message
            await message.clear_reactions()
            await message.edit(embed=embed)
            if archive_now:
                await ctx.channel.edit(archived=True)


    @command(name='ttm')
    async def toggle_monitoring(self, ctx: Context):
        if not ctx.author.guild_permissions.administrator:
            return await send_error_embed(ctx, 'This command can only be used by an administrator.')

        # Get list of monitored guilds
        invoked_guild = str(ctx.guild.id)
        monitored_guilds = self.db.child('thread_manager').child('monitored').get().val()
        if monitored_guilds is not None and invoked_guild in monitored_guilds:
            # Already in monitored list
            new_state = not monitored_guilds[invoked_guild]
        else:
            # Not in monitored list
            new_state = True

        self.db.child('thread_manager').child('monitored').update({f'{invoked_guild}': new_state})
        if new_state:
            # Immediately unarchive threads
            await self.unarchive_threads_guild(ctx.guild)
            return await send_success_embed(ctx, f'Threads in **{ctx.guild.name}** will be kept unarchived')
        return await send_success_embed(ctx, f'Threads in **{ctx.guild.name}** will be archived automatically')
