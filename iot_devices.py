from flask import Blueprint
from flask import request, url_for, render_template, session, flash
import iot_db
from datetime import datetime
import devices

iot_devices = Blueprint('iot_devices', __name__)
module_names = [
    devices.unknown.name,
    devices.smartplug.name,
    devices.bluetooth.name,
    devices.usb.name,
    devices.infrared.name,
    devices.industrial.name,
    devices.multiplug.name,
    devices.audio.name,
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
        devices=user.devices, module_names=module_names)
