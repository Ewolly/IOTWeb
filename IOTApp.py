from __future__ import print_function
from flask import Flask, render_template
from authentication import auth
from werkzeug.contrib.fixers import ProxyFix
from iot_db import init_app
from iot_api import iot_api

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')
app.register_blueprint(auth)
app.register_blueprint(iot_api, url_prefix='/api/1')
app.wsgi_app = ProxyFix(app.wsgi_app)

init_app(app)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8000)
