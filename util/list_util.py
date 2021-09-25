from itertools import islice
from typing import Dict, List


def dict_chunks(data: Dict):
    it = iter(data)
    for i in range(0, len(data), 5):
        yield {k: data[k] for k in islice(it, 5)}


def list_chunks(data: List):
    for i in range(0, len(data), 10):
        yield islice(data, i, i + 10)
