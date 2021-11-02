from flask import Flask, render_template
from util import get_var

rico_dash = Flask(__name__)

@rico_dash.route('/')
def home():
    return render_template('index.html')

@rico_dash.route('/spotify_auth')
def welcome():
    return render_template('spotify_auth.html')

def serve_dash():
    print('Serving')
    rico_dash.run(threaded=True, host='0.0.0.0', port=get_var('FLASK_PORT'))
