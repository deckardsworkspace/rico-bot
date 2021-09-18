import os
import shutil
import subprocess
import requests
from config import get_var
from nextcord.ext.commands import Bot


def download_jar():
    if not os.path.exists('./Lavalink.jar'):
        # Get latest Lavalink release
        r = requests.get('https://api.github.com/repos/freyacodes/Lavalink/releases/latest')
        assets = r.json()['assets']
        if len(assets) and 'browser_download_url' in assets[0]:
            # Download jar file
            d = requests.get(assets[0]['browser_download_url'], stream=True)
            with open('./Lavalink.jar', 'wb') as jar_file:
                shutil.copyfileobj(d.raw, jar_file)
            del d
        else:
            raise Exception('Could not find latest Lavalink jar')


def create_yml():
    lavalink_port = get_var('PORT')
    lavalink_pass = get_var('LAVALINK_PASSWORD')

    with open('./application.template.yml', 'r') as file:
        lavalink_config = file.read()
    
    lavalink_config = lavalink_config.replace('LAVALINK_PORT', lavalink_port)
    lavalink_config = lavalink_config.replace('LAVALINK_PASSWORD', lavalink_pass)

    with open('./application.yml', 'w') as file:
        file.write(lavalink_config)


def bootstrap():
    os.chdir('./lavalink_server')
    download_jar()
    create_yml()
    return subprocess.Popen(['java', '-jar', 'Lavalink.jar'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
