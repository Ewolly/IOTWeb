from __future__ import print_function
from flask import Flask, render_template
from werkzeug.contrib.fixers import ProxyFix

from authentication import auth
import iot_db
from iot_api import iot_api
from iot_devices import iot_devices
import iot_sockets

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')
app.register_blueprint(auth)
app.register_blueprint(iot_api, url_prefix='/api/1')
app.register_blueprint(iot_devices)
app.wsgi_app = ProxyFix(app.wsgi_app)

iot_db.init_app(app)
iot_sockets.start_server()

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8000, use_reloader=False)
