from json import JSONEncoder
from collections import deque


class DequeEncoder(JSONEncoder):
    # https://stackoverflow.com/a/61273028
    def default(self, obj):
        if isinstance(obj, deque):
            return list(obj)
        return JSONEncoder.default(self, obj)
