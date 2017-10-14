from flask import Blueprint
from flask import request, url_for, render_template, session, flash, redirect
import iot_db
import json
from devices import device_modules
from iot_sockets import device_sockets
import copy

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

    online_devices = []
    offline_devices = []
    for device in user.devices:
        if device.ip_address is not None:
            if device.module_type == 4:
                ir_device = iot_db.Infrared.query.get(device.device_id)
                device.sensors = copy.deepcopy(ir_device.feedback)
                device.buttons = copy.deepcopy(ir_device.buttons)
            online_devices.append(device)
        else:
            offline_devices.append(device)

    return render_template('devices.html', 
        online_devices=online_devices,
        offline_devices=offline_devices, 
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
    for dev in user.devices:   
        if dev.device_id == device_id:
            break
    else:
        #check
        flash('Permission denied', 'error')
        return redirect(url_for('.list_devices'), 303)
    
    sensor_data = request.get_json(silent=True)
    if sensor_data is None:
        flash('Invalid Operation', 'error')
        return redirect(url_for('.list_devices'), 303)
    out_array = []
    for enabled, name in sensor_data:
        out_array.append({
            "enabled": enabled,
            "name": name,
            "input": False
            })
    ir_device.feedback = out_array
    iot_db.update_db()
    if device_id in device_sockets:
        device_sockets[device_id].send_message({'feedback': json.dumps(out_array)})
        print json.dumps(out_array)
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
        flash('Invalid Operation', 'error')
        return redirect(url_for('.list_devices'), 303)
    
    new_array = []
    for button_id, button_name in button_data.iteritems():
        new_array.append({
            "id" : int(button_id),
            "name": button_name,
            "continuous" : False,
            "pulses" : 2,
            "learnt": False
            })

    ir_device.buttons = new_array
    iot_db.update_db()
    return redirect(url_for('.list_devices'), 303)

@iot_devices.route('/device/<int:device_id>/button/<int:button_id>/learn', methods=['POST'])
def learn_button(device_id, button_id):
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
    
    for dev in user.devices:   
        if dev.device_id == device_id:
            break
    else:
        flash('Permission denied', 'error')
        return redirect(url_for('.list_devices'), 303)

    button = None
    for b in ir_device.buttons:
        if b['id'] == button_id:
            button = b
            break
    else:
        flash('button does not exist', 'error')
        return redirect(url_for('.list_devices'), 303)

    device_modules[4].learn_button(device_id, button_id)
    ir_device.learning = True
    iot_db.update_db()
    if button.get('name') is not None:
        flash("learning button '" + button['name'] + "'...", 'info')
    else:
        flash("learning button with id '" + str(button["id"]) + "'...", 'info')

    return redirect(url_for('.list_devices'), 303)

@iot_devices.route('/device/<int:device_id>/buttons/add', methods=['POST'])
def add_button(device_id):
    print request.data
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
        flash('Invalid Operation', 'error')
        return redirect(url_for('.list_devices'), 303)

    if ir_device.buttons is not None:
        for button_old in ir_device.buttons:
            if button_update["id"] == button_old["id"]:
                flash('id already in use', 'warning')
                return redirect(url_for('.list_devices'), 303)
        new_but = ir_device.buttons[:]
    else:
        new_but = []
    new_but.append({
        "id" : int(button_update["id"]),
        "name": button_update["name"],
        "continuous" : False,
        "pulses" : 2,
        "learnt": button_update["learnt"]
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

    new_list = []
    for button_old in ir_device.buttons:
        if button_id != button_old["id"]:
            new_list.append(button_old)
    ir_device.buttons = new_list
    iot_db.update_db()
    return redirect(url_for('.list_devices'), 303)

@iot_devices.route('/device/<int:device_id>/delete', methods=['DELETE'])
def delete_device(device_id):
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

    if device.device_id in device_sockets:
        device_sockets[device.device_id].send_message({"server":"stop"})

    ir_device = iot_db.Infrared.query.get(device_id)
    if ir_device is not None:
        iot_db.drop_from_db(ir_device)

    iot_db.drop_from_db(device)
    iot_db.update_db()
    return redirect(url_for('.list_devices'), 303)