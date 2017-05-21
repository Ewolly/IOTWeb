from smartplug import Smartplug

class Infrared(Smartplug):
    name = 'infrared'

    @classmethod
    def device_details(cls, device, ir_device):
        return_dict = super(cls, self).device_details(device)

        if ir_device is not None:
            return_dict['feedback'] = ir_device.feedback
            return_dict['repeater'] = ir_device.repeater
            
            if ir_device.buttons is not None:
                return_dict['buttons'] = ir_device.buttons

        return return_dict