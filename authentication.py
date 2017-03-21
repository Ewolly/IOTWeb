from flask import Blueprint, current_app
from flask import redirect, request, g, render_template
from flask import Flask, session, redirect, url_for, escape
from oauth2client.client import OAuth2WebServerFlow
from hashlib import sha512
from db import Users
import os

oauth2 = Blueprint('oauth2', __name__)

app = Flask(__name__)

def get_flow():
    flow = getattr(g, '_flow', None)
    if flow is None:
        flow = g._flow = OAuth2WebServerFlow(
            client_id=current_app.config['CLIENT_ID'],
            client_secret=current_app.config['CLIENT_SECRET'],
            redirect_uri=current_app.config['CLIENT_REDIRECT_URI'],
            scope='email',
            user_agent='my-sample/1.0')
    return flow

@oauth2.route('/google-login')
def begin_auth():
    authorize_url = get_flow().step1_get_authorize_url()
    return redirect(authorize_url)

@oauth2.route('/oauth2callback')
def handle_oauth2_callback():
    code = request.args.get('code', None)
    if code is None:
        return 'Failure to authenticate. No code received.'

    credentials = get_flow().step2_exchange(code)
    return 'Email address: %s' % credentials.id_token['email']

@oauth2.route('/login', methods=['GET','POST'])
def login_request():
    if request.method == 'GET':
        return render_template('login.html')
    return validate_login(request.form['email'], request.form['password'])

def validate_login(email, password):
    hashed_password = sha512(password).hexdigest()
    user = Users.query.filter_by(email=email).first()
    if user == None:
        return redirect('/user-not-found')
    elif user.password == hashed_password:
        session['email'] = request.email
        return redirect('/devices')
    else:
        return redirect('/password-incorrect')

