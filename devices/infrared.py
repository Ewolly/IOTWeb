import smartplug
from smartplug import *

name = 'infrared'

def device_details(device, ir_device):
    return_dict = { }

    if ir_device is not None:
        return_dict['feedback'] = ir_device.feedback
        
        if ir_device.buttons is not None:
            return_dict['buttons'] = ir_device.buttons

    plug_dict = smartplug.device_details(device).copy()
    return_dict.update(plug_dict)
    return return_dict