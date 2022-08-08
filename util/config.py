from typing import Any, Dict, List
from yaml import safe_load


def get_config() -> Dict[str, Any]:
    try:
        with open('config.yml', 'r') as f:
            return safe_load(f)
    except FileNotFoundError:
        raise RuntimeError('config.yml not found')
    except Exception as e:
        raise RuntimeError(f'Error parsing config.yml: {e}')


def get_debug_status() -> bool:
    try:
        return get_config()['bot']['debug']['enabled']
    except KeyError:
        return False


def get_debug_guilds() -> List[int]:
    try:
        return get_config()['bot']['debug']['guild_ids']
    except KeyError:
        return []
