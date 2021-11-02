from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/spotify_auth')
def welcome():
    return render_template('spotify_auth.html')

def serve_app(port: int):
    app.run(port=port, debug=True)

if __name__ == '__main__':
    app.run()
