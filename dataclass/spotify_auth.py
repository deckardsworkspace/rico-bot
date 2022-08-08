from dataclasses import dataclass
from datetime import datetime


@dataclass
class SpotifyCredentials:
    user_id: int
    refresh_token: str
    access_token: str
    expires_at: datetime
