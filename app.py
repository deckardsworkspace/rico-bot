from discord import Client, Activity, ActivityType
from discord.ext.commands import Bot
import os
import pyrebase

pyrebase_config = {
    'apiKey': os.environ['FIREBASE_KEY'],
    'authDomain': os.environ['FIREBASE_AUTHDOMAIN'],
    'databaseURL': os.environ['FIREBASE_DBURL'],
    'storageBucket': os.environ['FIREBASE_BUCKET'],
    'serviceAccount': {
        'client_email': os.environ['FIREBASE_CLIENT_EMAIL'], 
        'client_id': os.environ['FIREBASE_CLIENT_ID'],
        'private_key': os.environ['FIREBASE_PRIVATE_KEY'].replace('\\n', '\n'),
        'private_key_id': os.environ['FIREBASE_PRIVATE_KEY_ID'],
        'type': 'service_account'
    },
}
firebase = pyrebase.initialize_app(pyrebase_config)
auth = firebase.auth()
db = firebase.database()
client = Bot(command_prefix='rc!')


@client.event
async def on_ready():
    db.child('test').push({'user': '{}'.format(client.user)})
    client.change_presence(activity=Activity(name='you | rc!help', type=ActivityType.listening))
    print('Logged on as {0}!'.format(client.user))


client.run(os.environ['DISCORD_TOKEN'])
