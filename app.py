from __future__ import print_function
from flask import Flask, render_template
from authentication import oauth2

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')
app.register_blueprint(oauth2)


@app.route('/')
@app.route('/<name>')
def say_hello(name="World"):
    return render_template('hello.html', name=name)

if __name__ == "__main__":
    app.run(host='127.0.0.1')