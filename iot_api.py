from flask import Blueprint
from flask import make_response, jsonify, request, url_for
from functools import wraps
from collections import namedtuple
import iot_db
from datetime import datetime
from devices import device_modules

iot_api = Blueprint('iot_api', __name__)

@iot_api.route('/heartbeat', methods=['GET'])
def heartbeat():
    return make_response(jsonify({'status': 'ok'}), 200)

@iot_api.route('/device/types', methods=['GET'])
def enumerate_devices():
    return make_response(
        jsonify(list(d.name for d in device_modules)))

@iot_api.route('/user/devices/list', methods=['GET'])
def list_devices():
    user, err_msg = check_credentials(
        request.headers.get('email'), 
        request.headers.get('password'))
    if user is None:
        return make_response(jsonify({'error': err_msg}), 400)
    
    response = []
    for device in user.devices:
        response.append({
            'device_id': device.device_id,
            'friendly_name': device.friendly_name,
            'module_type': device.module_type,
            'online': device.ip_address is not None,
            'url': url_for('.device_info', 
                device_id = device.device_id, _external=True)
        })
    return make_response(jsonify(response), 200)

@iot_api.route('/user/devices/details', methods=['GET'])
def device_details():
    user, err_msg = check_credentials(
        request.headers.get('email'), 
        request.headers.get('password'))
    if user is None:
        return make_response(jsonify({'error': err_msg}), 400)

    iot_db.update_db()

    response = []
    for device in user.devices:
        kwargs = {
            'device_id': device.device_id,
            'friendly_name': device.friendly_name,
            'module_type': device.module_type,
            'online': device.ip_address is not None,
            'first_connected': device.first_connected,
            'last_checked': device.last_checked,
            'url': url_for('.device_info', 
                device_id = device.device_id, _external=True)
        }
        if device.module_type == 4: # infrared
            details = device_modules[4].device_details(device,
                iot_db.Infrared.query.get(device.device_id))
        else:
            details = device_modules[device.module_type].device_details(device);
        kwargs.update(details)
        response.append(kwargs)
    return make_response(jsonify(response), 200)

@iot_api.route('/device/<int:device_id>/info', methods=['GET'])
def device_info(device_id):
    user, err_msg = check_credentials(
        request.headers.get('email'), 
        request.headers.get('password'))
    if user is None:
        return make_response(jsonify({'error': err_msg}), 400)

    iot_db.update_db()
    device = iot_db.Devices.query.get(device_id)
    if device is None:
        return make_response(jsonify({
            'error': 'device_id does not exist'}), 400)
    if device.user_id != user.user_id:
        return make_response(jsonify({
            'error': 'account does not have permission to ' +
                     'view this device'
            }), 400)


    return make_response(jsonify({
        'device_id': device.device_id,
        'user_id': device.user_id,
        'client_id': device.client_id,
        'module_type': device.module_type,
        'friendly_name': device.friendly_name,
        'ip_address': device.ip_address,
        'port': device.port,
        'first_connected': device.first_connected.isoformat(),
        'last_checked': device.last_checked.isoformat(),
        }), 200)

@iot_api.route('/device/register', methods=['PUT'])
def register_device():
    if not request.is_json:
        return make_response(jsonify({
            'error': 'request object must be application/json'
            }), 400)
    
    device_data = request.get_json(silent=True)
    if device_data is None:
        return make_response(jsonify({
            'error': 'error parsing json'
            }), 400)

    for field in ['email', 'module_type', 'setup_time']:
        if field not in device_data:
            return make_response(jsonify({
                'error': 'missing field: %s' % field
                }), 200)
    
    user_email = device_data['email']
    user = iot_db.get_user(user_email)
    if user is None:
        user = iot_db.Users(user_email, None)
        iot_db.add_to_db(user)
        iot_db.update_db()
    new_device = iot_db.Devices(
        user.user_id, device_data['module_type'], request.remote_addr,
        request.environ.get('REMOTE_PORT'), 
        device_data.get('friendly_name'))

    iot_db.add_to_db(new_device)
    iot_db.update_db()

    if new_device.module_type == 4:
        iot_db.add_to_db(iot_db.Infrared(new_device.device_id))
        iot_db.update_db()

    return make_response(jsonify({
        'device_id': new_device.device_id,
        'token': str(new_device.token),
        'device_url': url_for('.device_info', 
                device_id = new_device.device_id, _external=True)
        }), 200)

@iot_api.route('/device/<int:device_id>/deregister', methods=['DELETE'])
def deregister_device(device_id):
    device = iot_db.Devices.query.get(device_id)
    if device is None:
        return make_response(jsonify({
            'error': 'device does not exist'
            }), 400)

    user_email = request.headers.get('email')
    user_password = request.headers.get('password')
    token = request.headers.get('token')
    if token is not None and token == str(device.token):
        iot_db.drop_from_db(device)
        iot_db.update_db()
        return make_response(jsonify({'status': 'success'}), 200)

    if user_email is None:
        return make_response(jsonify({
            'error': 'missing email'
            }), 400)
    user = iot_db.get_user(user_email)
    if user is None:
        return make_response(jsonify({
            'error': 'account does not exist'
            }), 400)

    if user_password is None:
        if user.password is not None:
            return make_response(jsonify({
                'error': 'user account is setup (need password)'
                }), 400)
        else:
            iot_db.drop_from_db(user)
    else:
        if device.user_id != user.user_id:
            return make_response(jsonify({
                'error': 'account does not have permission to ' +
                         'delete this device'
                }), 400)
        if iot_db.hash_pass(user_email, user_password) != user.password:
            return make_response(jsonify({
                'error': 'password is incorrect'
                }), 200)

    iot_db.drop_from_db(device)
    iot_db.update_db()
    return make_response(jsonify({'status': 'success'}), 200)

@iot_api.route('/device/<int:device_id>/power/<any("on", "off"):state>', 
    methods=['POST'])
def power_device(device_id, state):
    user, err_msg = check_credentials(
        request.headers.get('email'), 
        request.headers.get('password'))
    if user is None:
        return make_response(jsonify({'error': err_msg}), 400)

    device = iot_db.Devices.query.get(device_id)
    if device is None:
        return make_response(jsonify({
            'error': 'device_id does not exist'}), 400)
    if device.user_id != user.user_id:
        return make_response(jsonify({
            'error': 'account does not have permission to ' +
                     'view this device'
            }), 400)

    device.plug_status = state == "on"
    iot_db.update_db()
    return make_response(jsonify({'status': 'success'}), 200)


@iot_api.route('/device/<int:device_id>/connect', methods=['POST'])
def connect_device(device_id):
    pass

@iot_api.route('/device/<int:device_id>/disconnect', methods=['DELETE'])
def disconnect_device(device_id):
    pass

@iot_api.route('/device/update', methods=['POST'])
def update_device():
    pass

def check_credentials(email, password):
    if email is None:
        return (None, 'missing email')
    if password is None:
        return (None, 'missing password')
    user = iot_db.get_user(email)
    hashed_password = iot_db.hash_pass(email, password)
    if user is None:
        return (None, 'account does not exist')
    if user.password != hashed_password:
        return (None, 'password is incorrect')
    return (user, None)

# ----------
# ir methods
# ----------
@iot_api.route('/device/<int:device_id>/repeater/<any("on", "off"):state>', 
    methods=['POST'])
def ir_repeater(device_id, state):
    user, err_msg = check_credentials(
        request.headers.get('email'), 
        request.headers.get('password'))
    if user is None:
        return make_response(jsonify({'error': err_msg}), 400)

    device = iot_db.Devices.query.get(device_id)
    if device is None:
        return make_response(jsonify({
            'error': 'device_id does not exist'}), 400)
    if device.user_id != user.user_id:
        return make_response(jsonify({
            'error': 'account does not have permission to ' +
                     'view this device'
            }), 400)

    if device.module_type != 4: # infrared
        return make_response(jsonify({
            'error': 'this device is not infrared'
            }), 400)

    ir_device = iot_db.Infrared.query.get(device_id)
    if ir_device == None:
        return make_response(jsonify({
            'error': 'missing infrared table entry'
            }), 400)

    ir_device.repeater = state == "on"
    iot_db.update_db()
    return make_response(jsonify({'status': 'success'}), 200)

@iot_api.route('/device/<int:device_id>/ir/<int:button_id>/' + 
    '<any("start", "stop", "single"):state>', methods=['PUT'])
def ir_button_state(device_id, button_id, state):
    user, err_msg = check_credentials(
        request.headers.get('email'), 
        request.headers.get('password'))
    if user is None:
        return make_response(jsonify({'error': err_msg}), 400)

    device = iot_db.Devices.query.get(device_id)
    if device is None:
        return make_response(jsonify({
            'error': 'device_id does not exist'}), 400)
    if device.user_id != user.user_id:
        return make_response(jsonify({
            'error': 'account does not have permission to ' +
                     'view this device'
            }), 400)

    if device.module_type != 4: # infrared
        return make_response(jsonify({
            'error': 'this device is not infrared'
            }), 400)

    ir_device = iot_db.Infrared.query.get(device_id)
    if ir_device is None:
        return make_response(jsonify({
            'error': 'missing infrared table entry'
            }), 400)

    if ir_device.buttons is None:
        return make_response(jsonify({
            'error': 'no buttons defined'
            }), 400)

    button = None
    for b in ir_device.buttons:
        if b.get("id") == button_id:
            button = b
            break

    if button is None:
        return make_response(jsonify({
            'error': 'button ' + str(button_id) + 
                     'not defined'
            }), 400)

    # TODO: send button.pulses
    cont = button.get("continuous")
    if cont is None:
        return make_response(jsonify({'error': 'continuous not set'}), 400)
    elif cont:
        if state == "on" or state == "off":
            # TODO: implement this
            return make_response(jsonify({'status': 'success'}), 200)
        else:
            return make_response(jsonify({'error': 'expected "on" or "off"'}), 400)
    else:
        if state == "single":
            # TODO: implement this
            return make_response(jsonify({'status': 'success'}), 200)
        else:
            return make_response(jsonify({'error': 'expected "single"'}), 400)

