from flask import Blueprint
from flask import request, url_for
import iot_db
from datetime import datetime

iot_api = Blueprint('iot_devices', __name__)

@iot_api.route('/devices')
def list_devices():
    return render_template('devices.html')
