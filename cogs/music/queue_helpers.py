from collections import deque
from typing import Deque, List, Union
from util import QueueEmptyError
from .deque_encoder import DequeEncoder
import json


def enqueue_db(self, guild_id: str, query: Union[str, List[str]]):
    queue = self.get_queue_db(guild_id)

    if isinstance(query, list):
        queue.extend(query)
    else:
        queue.append(query)

    self.set_queue_db(guild_id, queue)


def dequeue_db(self, guild_id: str) -> str:
    queue = self.get_queue_db(guild_id)
    if not len(queue):
        raise QueueEmptyError()

    query = queue.popleft()
    self.set_queue_db(guild_id, queue)
    return query


def get_queue_db(self, guild_id: str) -> Deque[str]:
    queue_items = self.db.child('player').child(guild_id).child('queue').get().val()
    if queue_items:
        return deque(json.loads(queue_items))
    return deque([])


def set_queue_db(self, guild_id: str, queue: Deque[str]):
    self.db.child('player').child(guild_id).child('queue').set(json.dumps(queue, cls=DequeEncoder))
