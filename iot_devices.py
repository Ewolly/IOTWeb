from flask import Blueprint
from flask import request, url_for, render_template, session, flash
import iot_db
from datetime import datetime
from devices import device_modules

iot_devices = Blueprint('iot_devices', __name__)

@iot_devices.route('/devices')
def list_devices():
    user_id = session.get('id')
    if user_id is None:
        flash('Please login.', 'warning')
        return redirect(url_for('auth.login_request'), 303)
    user = iot_db.Users.query.get(user_id)
    if user is None:
        flash('User does not exist.', 'error')
        return redirect(url_for('auth.login_request'), 303)
    return render_template('devices.html', 
        online_devices=[dev for dev in user.devices if dev.ip_address is not None],
        offline_devices=[dev for dev in user.devices if dev.ip_address is None], 
        module_names=[x.name for x in device_modules])
