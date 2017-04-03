from flask import Blueprint
from flask import request, url_for, render_template
import iot_db
from datetime import datetime

iot_devices = Blueprint('iot_devices', __name__)

@iot_devices.route('/devices')
def list_devices():
    return render_template('devices.html')
