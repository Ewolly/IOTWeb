from __future__ import print_function
from flask import Flask, render_template
from authentication import oauth2
from werkzeug.contrib.fixers import ProxyFix
from db import init_app

app = Flask(__name__, instance_relative_config=True)
init_app(app)
app.config.from_pyfile('config.py')
app.register_blueprint(oauth2)
app.wsgi_app = ProxyFix(app.wsgi_app)


@app.route('/')
@app.route('/<title>')
@app.route('/<title>/<text>')
def enter_text(title="Hello World", text=""):
    return render_template('hello.html', 
        title=title, text=text)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8000)