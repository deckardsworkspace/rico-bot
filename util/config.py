import os


def get_var(key: str):
    if key in os.environ:
        return os.environ[key]
    raise RuntimeError(f'Missing configuration key {key}. Please check your build vars.')


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
