from itertools import islice


def dict_chunks(data):
    it = iter(data)
    for i in range(0, len(data), 5):
        yield {k: data[k] for k in islice(it, 5)}
