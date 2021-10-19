import json
import os
from .string_util import check_ip_addr, check_url


required_lavalink_keys = ['id', 'region', 'server', 'password']


def get_lavalink_nodes():
    nodes_str = get_var('LAVALINK')

    try:
        nodes = json.loads(nodes_str.replace('\\"', '\"'))
        if not isinstance(nodes, list):
            raise RuntimeError('$LAVALINK must be a list of nodes.')
        if not len(nodes):
            raise RuntimeError('$LAVALINK must not be an empty list.')
        
        # Check that each node info is complete
        for i, node in enumerate(nodes):
            for key in required_lavalink_keys:
                if key not in node.keys():
                    raise KeyError(f'Node {i+1} in $LAVALINK is missing the key "{key}".')
                if key == 'server':
                    # Check valid server format
                    node_server = node['server']
                    server_info = node_server.split(':', 1)
                    if len(server_info) != 2:
                        raise KeyError(f'Invalid server for node {i+1}. Please follow the format `something.com:port`.')
                    if not server_info[1].isnumeric():
                        raise KeyError(f'Invalid port for node {i+1}.')
                    if not check_url(server_info[0]):
                        if server_info[0] != 'localhost' and not check_ip_addr(server_info[0]):
                            raise KeyError(f'Invalid hostname or address for node {i+1}')

                    # Server is valid
                    del nodes[i]['server']
                    nodes[i]['host'] = server_info[0]
                    nodes[i]['port'] = server_info[1]

        return nodes
    except json.decoder.JSONDecodeError:
        raise RuntimeError('Invalid JSON found in $LAVALINK. Please check your build vars.')    


def get_var(key: str):
    if key in os.environ:
        return os.environ[key]
    raise RuntimeError(f'Missing configuration key ${key}. Please check your build vars.')


def get_pyrebase_config():
    return {
        'apiKey': get_var('FIREBASE_KEY'),
        'authDomain': get_var('FIREBASE_AUTHDOMAIN'),
        'databaseURL': get_var('FIREBASE_DBURL'),
        'storageBucket': get_var('FIREBASE_BUCKET'),
        'serviceAccount': {
            'client_email': get_var('FIREBASE_CLIENT_EMAIL'),
            'client_id': get_var('FIREBASE_CLIENT_ID'),
            'private_key': get_var('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
            'private_key_id': get_var('FIREBASE_PRIVATE_KEY_ID'),
            'type': 'service_account'
        },
    }
