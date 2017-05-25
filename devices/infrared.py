from smartplug import Smartplug
from iot_sockets import device_sockets

class Infrared(Smartplug):
    name = 'infrared'

    @classmethod
    def device_details(self, device, ir_device):
        return_dict = super(Infrared, self).device_details(device)

        if ir_device is not None:
            return_dict['feedback'] = ir_device.feedback
            return_dict['repeater'] = ir_device.repeater
            
            if ir_device.buttons is not None:
                return_dict['buttons'] = ir_device.buttons

        return return_dict

    @staticmethod
    def send_button(device_id, button_id, action):
        if device_id in device_sockets:
            device_sockets[device_id].send_message({
                "ir_button": [button_id, action]
            })

    @classmethod
    def start_server(self, device_id, ir_device):
        super(Infrared, self).device_details(device_id, 'infrared')
        ir_device.connecting = 1