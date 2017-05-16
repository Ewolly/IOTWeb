name = 'smartplug'

def device_details(device):
    return_dict = {'plug_status': device.plug_status}
    if (device.current_consumption is not None):
        return_dict['current_consumption'] = device.current_consumption
    
    return return_dict

def set_plug(device, status):
    pass