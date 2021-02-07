def ellipsis_truncate(string):
    if len(string) < 200:
        return string
    return string[:196] + "..."
