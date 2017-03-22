from flask import Blueprint, current_app
from flask import redirect, request, g, render_template
from flask import session, redirect, url_for, make_response
from oauth2client.client import OAuth2WebServerFlow
from hashlib import sha512
from sqlalchemy import func
from db import Users, add_to_db, update_db
import os
import re

auth = Blueprint('auth', __name__)

@auth.route('/google-login')
def begin_auth():
    authorize_url = get_flow().step1_get_authorize_url()
    return redirect(authorize_url)

@auth.route('/login-callback')
def handle_oauth2_callback():
    code = request.args.get('code', None)
    if code is None:
        return 'Failure to authenticate. No code received.'

    credentials = get_flow().step2_exchange(code)
    return 'Email address: %s' % credentials.id_token['email']

@auth.route('/login', methods=['GET','POST'])
def login_request():
    if request.method == 'GET':
        return render_template('login.html')
    return validate_login(request.form['email'], request.form['password'])

def validate_login(email, password):
    email = email.strip()
    hashed_password = sha512(password).hexdigest()
    user = Users.query.filter(func.lower(Users.email) == email.lower()).first()
    
    if user == None:
        flash("User '%s' not found." % email, 'error')
    elif user.password != hashed_password:
        flash('The entered password is incorrect.', 'error')
    else:
        session['email'] = email
        session['id'] = user.user_id
        flash('Welcome, %s.' % email, 'info')
        return redirect('/devices')
    return redirect(url_for('login_request'), 303)

@auth.route('/sign-up', methods=['GET','POST'])
def sign_up():
    if request.method == 'GET':
        return render_template('sign_up.html')
        
    email = request.form.get('email', '').strip()
    password = request.form.get('password')
    repeat_password =  request.form.get('password_check')
    
    if email == '':
        flash('Invalid request (email missing).', 'error')
    elif password is None:
        flash('Invalid request (password missing).', 'error')
    elif repeat_password is None:
        flash('Invalid request (repeated password missing).', 'error')
    elif re.match(r'[^@]+@[^@]+', email) is None:
        flash('Invalid email address.', 'error')
    elif len(password) < 8:
        flash('Password too short.', 'error')
    elif password != repeat_password:
        flash('The entered passwords do not match.', 'error')
    elif not request.form.get('terms'):
        flash('Please accept the Terms and Conditions.', 'error')
    elif Users.query.filter(func.lower(Users.email) == email.lower()).first() is None:
        flash('This account already exists.', 'info')
        return redirect(url_for('login_request'), 303)
    else:
        new_user = Users(email, request.form['password'])
        add_to_db(new_user)
        update_db()
        flash('Account created successfully.', 'success')
        flash('Welcome, %s.' % email, 'info')
        session['email'] = email
        session['id'] = user.user_id
        return redirect('/devices', 303)
    return redirect(url_for('sign_up'), 303)
