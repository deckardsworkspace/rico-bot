from itertools import islice
from typing import Any, Dict, List


def dict_chunks(data: Dict[Any, Any]):
    it = iter(data)
    for _ in range(0, len(data), 5):
        yield {k: data[k] for k in islice(it, 5)}
