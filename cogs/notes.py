from dataclass.custom_embed import CustomEmbed, create_error_embed, create_success_embed
from dataclass.note import Note
from nextcord import Guild, Interaction, slash_command, SlashOption, User
from nextcord.ext import application_checks
from nextcord.ext.commands import Cog
from typing import List, Optional, TYPE_CHECKING
from util.config import get_debug_guilds
from util.list_util import list_chunks
from util.paginator import Paginator
from util.note_parser import create_note

if TYPE_CHECKING:
    from util.rico_bot import RicoBot


async def paginate_notes(itx: Interaction, owner: str, notes: List[Note]):
    # Create pages
    pages = []
    for chunk in list_chunks(notes, 5):
        fields = []
        item: Note
        for item in chunk:
            fields.append([
                item.title,
                '\n'.join([x for x in [
                    item.url,
                    f'added by <@{item.sender}> <t:{int(item.timestamp.timestamp())}:R>',
                    f'ID `{item.id}`'
                ] if x])
            ])

        # Create embed
        pages.append(CustomEmbed(
            title=f'Notes for {owner}',
            description=f'{len(notes)} total',
            fields=fields
        ).get())

    # Run paginator
    paginator = Paginator(itx)
    await paginator.run(pages)


class NotesCog(Cog):
    def __init__(self, bot: 'RicoBot'):
        self._bot = bot
        print(f'Loaded cog: {self.__class__.__name__}')

    def _ensure_records(self, guild: Optional[Guild] = None, user: Optional[User] = None):
        if guild:
            self._bot.api.update_guild(guild.id, guild.name)
        if user:
            self._bot.api.update_user(user.id, user.name, user.discriminator)

    @slash_command(name='addnote', guild_ids=get_debug_guilds())
    async def add_note(
            self,
            itx: Interaction,
            note: str = SlashOption(
                description='URL or text to add to their list',
                required=True
            ),
            recipient: User = SlashOption(
                description='User to add the note to.',
                required=True
            )):
        """
        Add a note to someone's list.
        """
        await itx.response.defer()

        # Make sure sender and recipient are both in database
        sender = itx.user.id
        self._ensure_records(guild=itx.guild, user=itx.user)
        self._ensure_records(user=recipient)

        # Add note to recipient's list
        note = create_note(self._bot.spotify, note, sender, recipient.id)
        self._bot.api.add_user_note(recipient.id, note)
        await itx.followup.send(embed=create_success_embed(
            title='Note added',
            body=f'**{note.title}** added to {recipient.mention}\'s list.'
        ))

    @slash_command(name='svr-addnote', guild_ids=get_debug_guilds())
    @application_checks.guild_only()
    async def add_server_note(
            self,
            itx: Interaction,
            note: str = SlashOption(
                description='URL or text to add to the server\'s list',
                required=True
            )):
        """
        Add a note to the server's list.
        """
        await itx.response.defer()

        # Ensure sender is in database
        sender = itx.user.id
        self._ensure_records(guild=itx.guild, user=itx.user)

        # Add note to server's list
        note = create_note(self._bot.spotify, note, sender, itx.guild_id)
        self._bot.api.add_guild_note(itx.guild_id, note)
        await itx.followup.send(embed=create_success_embed(
            title='Note added',
            body=f'**{note.title}** added to this server\'s list.'
        ))

    @slash_command(name='listnotes', guild_ids=get_debug_guilds())
    async def list(self, itx: Interaction):
        """
        Display your list of notes.
        """
        await itx.response.defer(ephemeral=True)

        # Get notes
        notes = self._bot.api.get_user_notes(itx.user.id)
        if not notes:
            return await itx.followup.send(embed=create_error_embed(body='You have no notes.'))

        # Display notes
        await paginate_notes(itx, itx.user.name, notes)

    @slash_command(name='svr-listnotes', guild_ids=get_debug_guilds())
    @application_checks.guild_only()
    async def list_server(self, itx: Interaction):
        """
        Display the server's list of notes.
        """
        await itx.response.defer()

        # Get notes
        notes = self._bot.api.get_guild_notes(itx.guild_id)
        if not notes:
            return await itx.followup.send(embed=create_error_embed(body='The server doesn\'t have any notes.'))

        # Display notes
        await paginate_notes(itx, itx.guild.name, notes)

    @slash_command(name='removenote', guild_ids=get_debug_guilds())
    async def remove_note(
            self,
            itx: Interaction,
            note_id: Optional[str] = SlashOption(
                description='ID of the note to remove (get with `/listnotes`)',
                required=True
            )
    ):
        """
        Remove a note from your list.
        """
        await itx.response.defer(ephemeral=True)

        # Remove note
        try:
            self._bot.api.remove_user_note(itx.user.id, note_id)
        except Exception as e:
            return await itx.followup.send(embed=create_error_embed(body=str(e)))
        else:
            return await itx.followup.send(embed=create_success_embed(
                body=f'Note with ID `{note_id}` removed.'
            ))

    @slash_command(name='clearnotes', guild_ids=get_debug_guilds())
    async def clear_notes(self, itx: Interaction):
        """
        Clear all of your notes. Warning: irreversible!
        """
        await itx.response.defer(ephemeral=True)

        # Clear notes
        try:
            self._bot.api.clear_user_notes(itx.user.id)
        except Exception as e:
            return await itx.followup.send(embed=create_error_embed(body=str(e)))
        else:
            return await itx.followup.send(embed=create_success_embed(body='Cleared your notes'))

    @slash_command(name='svr-removenote', guild_ids=get_debug_guilds())
    @application_checks.guild_only()
    @application_checks.has_guild_permissions(administrator=True)
    async def remove_server_note(
            self,
            itx: Interaction,
            note_id: Optional[str] = SlashOption(
                description='ID of the note to remove (get with `/svr-listnotes`)',
                required=True
            )
    ):
        """
        Remove a note from the server's list.
        """
        await itx.response.defer()

        # Remove note
        try:
            self._bot.api.remove_guild_note(itx.guild_id, note_id)
        except Exception as e:
            return await itx.followup.send(embed=create_error_embed(body=str(e)))
        else:
            return await itx.followup.send(embed=create_success_embed(
                body=f'Note with ID `{note_id}` removed.'
            ))

    @slash_command(name='svr-clearnotes', guild_ids=get_debug_guilds())
    @application_checks.guild_only()
    @application_checks.has_guild_permissions(administrator=True)
    async def clear_notes(self, itx: Interaction):
        """
        Clear all the server's notes. Warning: irreversible!
        """
        await itx.response.defer()

        # Remove note
        try:
            self._bot.api.clear_guild_notes(itx.guild_id)
        except Exception as e:
            return await itx.followup.send(embed=create_error_embed(body=str(e)))
        else:
            return await itx.followup.send(embed=create_success_embed(body='Cleared all notes for this server'))
