import discord
import os
import pyrebase

pyrebase_config = {
    "apiKey": os.environ['FIREBASE_KEY'],
    "authDomain": os.environ['FIREBASE_AUTHDOMAIN'],
    "databaseURL": os.environ['FIREBASE_DBURL'],
    "storageBucket": os.environ['FIREBASE_BUCKET']
}
firebase = pyrebase.initialize_app(pyrebase_config)
auth = firebase.auth()
user = auth.sign_in_with_email_and_password(os.environ['FIREBASE_EMAIL'], os.environ['FIREBASE_PASSWORD'])
db = firebase.database()


class RicoClient(discord.Client):
    async def on_ready(self):
        results = db.child('test').push({'user': self.user})
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        print('Message from {0.author}: {0.content}'.format(message))


client = RicoClient()
client.run(os.environ['DISCORD_TOKEN'])

