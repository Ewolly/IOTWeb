import iot_db

class SmartPlug(object):
    name = 'smartplug'

    @staticmethod
    def device_details(device):
        return {'plug_status': device.plug_status}

    @staticmethod
    def set_plug(device, status):
        pass