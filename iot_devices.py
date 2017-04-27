from flask import Blueprint
from flask import request, url_for, render_template, session, flash
import iot_db
from datetime import datetime
import devices

iot_devices = Blueprint('iot_devices', __name__)
modules = [
    devices.unknown,
    devices.smartplug,
    devices.bluetooth,
    devices.usb,
    devices.infrared,
    devices.industrial,
    devices.multiplug,
    devices.audio,
]

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
        devices=user.devices, module_names=(x.name for x in modules))
