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
        # if device_id in device_sockets:
        #     device_sockets[device_id].send_message({
        #         "ir_button": [button_id, action]
        #     })
        if device_id not in device_sockets:                
            return

        if action == "start":
            command = 0x85
        else if action == "single":
            command = 0x84
        
        if action == "stop":
            device_sockets[device_id].send_message({
                "spi": {
                    "cmd": 0x86
                }})
        else:
            device_sockets[device_id].send_message({
                "spi": {
                    "cmd": command,
                    "data": button_id,
                    "len": 1
            })
    
    def learn_button(device_id, button_id):
        if device_id not in device_sockets:
            return

        device_sockets[device_id].send_message({
            "spi": {
                "cmd": 0x82,
                "data": button_id,
                "len": 1
                "resp_cmd": 0x02,
            }
        })

    def change_mode(device_id, repeater):
        if device_id not in device_sockets:
            return
        
        device_sockets[device_id].send_message({
            "spi": {
                "cmd": 0x87,
                "data": repeater,
                "len": 1
            }
        })

    def set_channel(device_id, channels):
        if device_id not in device_sockets:
            return

        device_sockets[device_id].send_message({
            "spi": {
                "cmd": 0x83,
                "data": channels,
                "len": 1
            }
        })
    
    def read_feedback(device_id, channels):
        if device_id not in device_sockets:
            return

        device_sockets[device_id].send_message({
            "spi": {
                "cmd": 0x03
            }
        })
    
    