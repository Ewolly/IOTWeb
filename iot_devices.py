from flask import Blueprint
from flask import request, url_for, render_template, session, flash, redirect
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

@iot_devices.route('/device/<int:device_id>/name/<new_name>', methods=['POST'])
def update_friendly_name(device_id, new_name):
    user_id = session.get('id')
    if user_id is None:
        flash('Please login.', 'warning')
        return redirect(url_for('auth.login_request'), 303)
    user = iot_db.Users.query.get(user_id)
    if user is None:
        flash('User does not exist.', 'error')
        return redirect(url_for('auth.login_request'), 303)
    device = iot_db.Devices.query.get(device_id)
    if device is None:
        flash('Device does not exist', 'warning')
        return redirect(url_for('auth.login_request'), 303)
    if device not in user.devices:
        flash('Permission denied', 'error')
        return redirect(url_for('.list_devices'), 303)
    device.friendly_name = new_name
    iot_db.update_db()
    return redirect(url_for('.list_devices'), 303)

@iot_devices.route('/device/<int:device_id>/sensors/update', methods=['POST'])
def update_sensors(device_id):
    user_id = session.get('id')
    if user_id is None:
        flash('Please login.', 'warning')
        return redirect(url_for('auth.login_request'), 303)
    user = iot_db.Users.query.get(user_id)
    if user is None:
        flash('User does not exist.', 'error')
        return redirect(url_for('auth.login_request'), 303)
    ir_device = iot_db.Infrared.query.get(device_id)
    if ir_device is None:
        flash('Device does not exist', 'warning')
        return redirect(url_for('auth.login_request'), 303)
    for  dev in user.devices:   
        if dev.device_id == device_id:
            break
    else:
        #check
        flash('Permission denied', 'error')
        return redirect(url_for('.list_devices'), 303)
    
    sensor_data = request.get_json(silent=True)
    if sensor_data is None:
        return make_response(jsonify({'error': 'missing field: %s' % field}), 200)
    out_array = []
    for enabled, name in sensor_data:
        out_array.append({
            "enabled": enabled,
            "name": name,
            "input": False
            })
    ir_device.feedback = out_array
    iot_db.update_db()
    return redirect(url_for('.list_devices'), 303)



@iot_devices.route('/device/<int:device_id>/buttons/update', methods=['POST'])
def update_buttons(device_id):
    user_id = session.get('id')
    if user_id is None:
        flash('Please login.', 'warning')
        return redirect(url_for('auth.login_request'), 303)
    user = iot_db.Users.query.get(user_id)
    if user is None:
        flash('User does not exist.', 'error')
        return redirect(url_for('auth.login_request'), 303)
    ir_device = iot_db.Infrared.query.get(device_id)
    if ir_device is None:
        flash('Device does not exist', 'warning')
        return redirect(url_for('auth.login_request'), 303)
    for  dev in user.devices:   
        if dev.device_id == device_id:
            break
    else:
        #check
        flash('Permission denied', 'error')
        return redirect(url_for('.list_devices'), 303)

    button_data = request.get_json(silent=True)
    if button_data is None:
        return make_response(jsonify({'error': 'missing field: %s' % field}), 200)
    
    new_array = []
    for button_id, button_name in button_data.iteritems():
        new_array.append({
            "id" : int(button_id),
            "name": button_name,
            "continuous" : False,
            "pulses" : 2
            })

    ir_device.buttons = new_array
    iot_db.update_db()
    return redirect(url_for('.list_devices'), 303)

@iot_devices.route('/device/<int:device_id>/buttons/add', methods=['POST'])
def add_button(device_id):
    user_id = session.get('id')
    if user_id is None:
        flash('Please login.', 'warning')
        return redirect(url_for('auth.login_request'), 303)
    user = iot_db.Users.query.get(user_id)
    if user is None:
        flash('User does not exist.', 'error')
        return redirect(url_for('auth.login_request'), 303)
    ir_device = iot_db.Infrared.query.get(device_id)
    if ir_device is None:
        flash('Device does not exist', 'warning')
        return redirect(url_for('auth.login_request'), 303)
    for  dev in user.devices:   
        if dev.device_id == device_id:
            break
    else:
        #check
        flash('Permission denied', 'error')
        return redirect(url_for('.list_devices'), 303)

    button_update = request.get_json(silent=True)
    if button_update is None:
        return make_response(jsonify({'error': 'missing field: %s' % field}), 200)

    for button_old in ir_device.buttons:
        if button_update["id"] == button_old["id"]:
            flash('id already in use', 'warning')
            return redirect(url_for('.list_devices'), 303)
    new_but = ir_device.buttons[:]
    new_but.append({
        "id" : int(button_update["id"]),
        "name": button_update["name"],
        "continuous" : False,
        "pulses" : 2
        })
    ir_device.buttons = new_but
    iot_db.update_db()
    return redirect(url_for('.list_devices'), 303)


@iot_devices.route('/device/<int:device_id>/button/<int:button_id>/delete', methods=['DELETE'])
def delete_button(device_id, button_id):
    user_id = session.get('id')
    if user_id is None:
        flash('Please login.', 'warning')
        return redirect(url_for('auth.login_request'), 303)
    user = iot_db.Users.query.get(user_id)
    if user is None:
        flash('User does not exist.', 'error')
        return redirect(url_for('auth.login_request'), 303)
    ir_device = iot_db.Infrared.query.get(device_id)
    if ir_device is None:
        flash('Device does not exist', 'warning')
        return redirect(url_for('auth.login_request'), 303)
    for  dev in user.devices:   
        if dev.device_id == device_id:
            break
    else:
        #check
        flash('Permission denied', 'error')
        return redirect(url_for('.list_devices'), 303)

    # button_delete = request.get_json(silent=True)
    # if button_delete is None:
    #     return make_response(jsonify({'error': 'missing field: %s' % field}), 200)


    new_list = []
    for button_old in ir_device.buttons:
        if button_id != button_old["id"]:
            new_list.append(button_old)
    ir_device.buttons = new_list
    iot_db.update_db()
    return redirect(url_for('.list_devices'), 303)