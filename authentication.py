from flask import Blueprint, current_app
from flask import redirect, request, render_template, flash, session, url_for
from hashlib import sha512
import iot_db
import os
import re
from iot_email import send_mail
import random, string
from datetime import datetime


auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET','POST'])
def login_request():
    if request.method == 'GET':
        return render_template('login.html')
    return validate_login(request.form['email'], request.form['password'])

def validate_login(email, password):
    email = email.strip()
    user = iot_db.get_user(email)
    if user == None:
        flash("User '%s' not found." % email, 'error')
    elif user.password != iot_db.hash_pass(email, password):
        flash('The entered password is incorrect.', 'error')
    else:
        session['email'] = email
        session['id'] = user.user_id
        flash('Welcome, %s.' % email, 'info')
        return redirect('/devices')
    return redirect(url_for('auth.login_request'), 303)

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
    elif iot_db.get_user(email) is not None:
        flash('This account already exists.', 'info')
        return redirect(url_for('auth.login_request'), 303)
    else:
        new_user = iot_db.Users(email, request.form['password'])
        iot_db.add_to_db(new_user)
        iot_db.update_db()
        flash('Account created successfully.', 'success')
        flash('Welcome, %s.' % email, 'info')
        session['email'] = email
        session['id'] = new_user.user_id
        return redirect('/devices', 303)
    return redirect(url_for('auth.sign_up'), 303)


@auth.route('/password-reset', methods=['GET','POST'])
def reset():
    if request.method == 'GET':
        return render_template('password_reset.html')

    email = request.form.get('email', '').strip()
    if email == '':
        flash('Invalid request (email missing).', 'error')
        return redirect(url_for('auth.reset'), 303)
    user = iot_db.get_user(email)
    if user is None:
        flash('This account does not exist', 'error')
        return redirect(url_for('auth.reset'), 303)
    user.nonce = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))
    user.password_reset_time = datetime.utcnow()
    iot_db.update_db()
    send_mail(email, 'Password reset code', 
        render_template('password_reset_email.html', email=email, nonce = user.nonce),
        current_app.config['SECRET_EMAIL'])
    return redirect(url_for('auth.reset_confirmed', email=email), 303)


@auth.route('/reset-confirmation')
def reset_confirmed():
    email = request.args.get('email')
    nonce = request.args.get('code')

    if email is None:
        flash('email is none', 'info')
        return render_template('code_confirmation.html', email="")
    if nonce is None:
        flash('nonce is none', 'info')
        return render_template('code_confirmation.html', email=email)
    user = iot_db.get_user(email)
    if user is None:
        flash('email does not exist', 'error')
        return render_template('code_confirmation.html', email=email)
    if user.nonce == nonce:
        flash('Password Reset Confirmed', 'info')
        session['email'] = email
        session['nonce'] = nonce
        return redirect(url_for('auth.new_password'), 303)
    flash('nonce is incorrect', 'error')
    return render_template('code_confirmation.html')
    
@auth.route('/confirm-password-reset', methods=['GET', 'POST'])
def new_password():
    email = session.get("email")
    nonce = session.get("nonce")

    if email is None or nonce is None:
        flash('stop trying to hack us', 'error')
        return redirect(url_for('auth.reset_confirmed'), 303)

    user = iot_db.get_user(email)
    if user is None:
        flash('create an account first', 'error')
        return redirect(url_for('auth.reset_confirmed'), 303)
    if nonce != user.nonce:
        flash('try again', 'error')
        return redirect(url_for('auth.reset_confirmed'), 303)

    if request.method == 'GET':
        return render_template('new_password.html')

    password = request.form.get('new_password')
    password_check = request.form.get('new_password_check')
    if password == password_check:
        user.password = password
        iot_db.update_db()
        return render_template('login.html')
    flash('passwords did not match', 'error')
    return redirect(url_for('auth.new_password'), 303)




