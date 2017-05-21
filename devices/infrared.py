from smartplug import Smartplug

class Infrared(Smartplug):
    name = 'infrared'

    @staticmethod
    def device_details(device, ir_device):
        return_dict = Smartplug.device_details(device)

        if ir_device is not None:
            return_dict['feedback'] = ir_device.feedback
            return_dict['repeater'] = ir_device.repeater
            
            if ir_device.buttons is not None:
                return_dict['buttons'] = ir_device.buttons

        return return_dict