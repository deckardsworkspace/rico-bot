from dataclass.note import Note
from requests import JSONDecodeError
from requests.auth import HTTPBasicAuth
from typing import Any, Dict, List, Optional
from util.config import get_debug_status
from .note_parser import create_note_from_db
import requests


class APIClient:
    def __init__(self, config: Dict[str, Any]):
        self._debug = get_debug_status()

        try:
            # Build auth header
            auth_username = config['backend']['auth']['username']
            auth_password = config['backend']['auth']['password']
            self._auth = HTTPBasicAuth(auth_username, auth_password)

            # Get API base URL
            api_host = config['backend']['host']
            api_port = config['backend']['port']
            api_prefix = config['backend']['prefix']
            self._base_url = f'http://{api_host}:{api_port}{api_prefix}'
        except KeyError as e:
            raise RuntimeError(f'Missing required config for API: {e}')

        # Create API session
        self._sesh = requests.Session()
        self._sesh.verify = False

    def _call(self, endpoint: str, verb: Optional[str] = 'GET', data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Use session to make request to API endpoint
        """
        url = f'{self._base_url}{endpoint}'
        try:
            response = self._sesh.request(
                method=verb,
                url=url,
                auth=self._auth,
                json=data
            )

            # Pretty print
            if self._debug:
                req = response.request
                print('{}\n{}\r\n{}\r\n\r\n{}'.format(
                    '-----------START-----------',
                    req.method + ' ' + req.url,
                    '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
                    req.body,
                ))

            body = response.json()
            if response.status_code != 200:
                raise RuntimeError(f'{verb} {url} {response.status_code}: {body["error"]}')
        except JSONDecodeError as e:
            raise RuntimeError(f'{verb} {url}: Error decoding JSON ({e})\'')

        return body
    
    def update_guild(self, guild_id: int, guild_name: Optional[str] = None, manage_threads: Optional[bool] = None):
        """
        Update existing guild record, or create a new one if it doesn't exist
        """
        try:
            self._call('/guilds', verb='PUT', data={
                'id': guild_id,
                'name': guild_name
            })
        except RuntimeError:
            # Guild does not exist yet, create it
            self._call('/guilds', verb='POST', data={
                'id': guild_id,
                'name': guild_name,
                'manage_threads': False
            })

    def delete_guild(self, guild_id: int):
        """
        Delete guild record from DB
        """
        self._call('/guilds', verb='DELETE', data={
            'id': guild_id
        })
    
    def update_user(self, user_id: int, username: str, discriminator: str):
        """
        Insert new user record, or update existing record if user already exists
        """
        self._call('/users', verb='PUT', data={
            'id': user_id,
            'name': username,
            'discriminator': discriminator
        })

    def delete_user(self, user_id: int):
        """
        Delete user record from DB
        """
        self._call('/users', verb='DELETE', data={
            'id': user_id
        })
    
    def add_user_note(self, user_id: int, note: Note):
        """
        Add note to user notes table in DB
        """
        self._call('/notes', verb='POST', data={
            'for_guild': False,
            'sender': note.sender,
            'recipient': user_id,
            'type': note.type.value,
            'title': note.title,
            'url': note.url
        })

    def get_user_notes(self, user_id: int) -> List[Note]:
        """
        Get all notes for a user
        """
        notes = self._call('/notes', data={
            'for_guild': False,
            'owner': user_id
        })
        return [create_note_from_db(note) for note in notes]
    
    def remove_user_note(self, user_id: int, note_id: str):
        """
        Remove note from user notes table in DB
        """
        self._call('/notes', verb='DELETE', data={
            'for_guild': False,
            'owner': user_id,
            'id': note_id
        })
    
    def clear_user_notes(self, user_id: int):
        """
        Remove all notes for a user
        """
        self._call('/notes', verb='DELETE', data={
            'for_guild': False,
            'owner': user_id,
            'delete_all': True
        })

    def add_guild_note(self, guild_id: int, note: Note):
        """
        Add note to guild notes table in DB
        """
        self._call('/notes', verb='POST', data={
           'for_guild': True,
           'sender': note.sender,
           'recipient': guild_id,
           'type': note.type.value,
           'title': note.title,
           'url': note.url
       })
    
    def get_guild_notes(self, guild_id: int) -> List[Note]:
        """
        Get all notes for a guild
        """
        notes = self._call('/notes', data={
            'for_guild': True,
            'owner': guild_id
        })
        return [create_note_from_db(note) for note in notes]
    
    def remove_guild_note(self, guild_id: int, note_id: str):
        """
        Remove note from guild notes table in DB
        """
        self._call('/notes', verb='DELETE', data={
            'for_guild': True,
            'owner': guild_id,
            'id': note_id
        })
    
    def clear_guild_notes(self, guild_id: int):
        """
        Remove all notes for a guild
        """
        self._call('/notes', verb='DELETE', data={
            'for_guild': False,
            'owner': guild_id,
            'delete_all': True
        })
    
    def add_excluded_thread(self, guild_id: int, thread_id: int):
        """
        Exclude a thread from being archived in a guild
        """
        self._call('/excluded_threads', verb='POST', data={
            'guild_id': guild_id,
            'thread_id': thread_id
        })

    def get_excluded_threads(self, guild_id: int) -> List[int]:
        """
        Get all excluded threads for a guild
        """
        response = self._call('/excluded_threads', data={
            'guild_id': guild_id
        })
        return response['excluded_threads']

    def check_excluded_thread(self, guild_id: int, thread_id: int) -> bool:
        """
        Check if a thread is excluded from being archived in a guild
        """
        return thread_id in self.get_excluded_threads(guild_id)
    
    def remove_excluded_thread(self, guild_id: int, thread_id: int):
        """
        Remove excluded thread from guild
        """
        self._call('/excluded_threads', verb='DELETE', data={
            'guild_id': guild_id,
            'thread_id': thread_id
        })
    
    def get_thread_manage_status(self, guild_id: int) -> bool:
        """
        Check whether threads are being automatically unarchived in a guild
        """
        response = self._call('/guilds', data={
            'id': guild_id
        })
        return response['guild']['manage_threads']

    def set_thread_manage_status(self, guild_id: int, status: bool):
        """
        Set whether threads are being automatically unarchived in a guild
        """
        self._call('/guilds', verb='PUT', data={
            'id': guild_id,
            'manage_threads': status
        })

    def get_thread_managed_guilds(self) -> List[int]:
        """
        Return a list of IDs of all guilds whose threads are being managed
        """
        response = self._call('/excluded_threads/guilds')
        return response['guilds']
