import smartplug
from smartplug import *

name = 'infrared'

def device_details(device):
    return_dict = { }
    
    if device.infrared is not None:
        return_dict['feedback'] = device.infrared.feedback
        
        if device.infrared.buttons is not None:
            return_dict['buttons'] = device.infrared.buttons

    plug_dict = smartplug.device_details(device).copy()
    return_dict.update(plug_dict)
    return return_dict