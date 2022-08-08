from dataclasses import dataclass
from datetime import datetime
from util.enums import NoteType


@dataclass
class Note:
    id: str
    timestamp: datetime
    sender: int
    recipient: int
    type: NoteType
    title: str
    url: str
