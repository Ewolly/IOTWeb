from flask import Blueprint
from flask import redirect, request, render_template, flash, session, url_for
from hashlib import sha512
from sqlalchemy import func
from db import Users, add_to_db, update_db
import os
import re
from email import send_mail

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET','POST'])
def login_request():
    if request.method == 'GET':
        return render_template('login.html')
    return validate_login(request.form['email'], request.form['password'])

def validate_login(email, password):
    email = email.strip()
    hashed_password = sha512(password+email).hexdigest()
    user = Users.get_user(email)
    if user == None:
        flash("User '%s' not found." % email, 'error')
    elif user.password != hashed_password:
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
    elif Users.get_user(email) is not None:
        flash('This account already exists.', 'info')
        return redirect(url_for('auth.login_request'), 303)
    else:
        new_user = Users(email, request.form['password'])
        add_to_db(new_user)
        update_db()
        flash('Account created successfully.', 'success')
        flash('Welcome, %s.' % email, 'info')
        session['email'] = email
        session['id'] = new_user.user_id
        return redirect('/devices', 303)
    return redirect(url_for('auth.sign_up'), 303)


@auth.route('/password-reset', methods=['GET','POST'])
def reset()
    if request.method == 'GET':
        return render_template('password_reset.html')

    email = request.form.get('email', '').strip()

    if email == '':
        flash('Invalid request (email missing).', 'error')
        return
    if re.match(r'[^@]+@[^@]+', email) is None:
        flash('Invalid email address.', 'error')
        return
    user = Users.get_user(email)
    if user is None:
        flash('This account does not exist', 'error')
        return
    user.nonce = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))
    user.password_reset_time = datetime.utcnow()
    update_db()
    send_mail(email, 'Password reset code','your password rest code is: '+user.nonce)

@auth.route('/reset-confirmation')
def reset_confirmed()
