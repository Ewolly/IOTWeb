from iot_sockets import device_sockets

class Smartplug(object):
    name = 'smartplug'

    @staticmethod
    def device_details(device):
        return_dict = {'plug_status': device.plug_status}
        if (device.current_consumption is not None):
            return_dict['current_consumption'] = int(device.current_consumption)
        
        return return_dict

    @staticmethod
    def set_plug(device_id, status):
        if device_id in device_sockets:
            device_sockets[device_id].send_message({"power": status})