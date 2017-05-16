name = 'smartplug'

def device_details(device):
    return {
        'plug_status': device.plug_status,
        'current_consumption': device.current_consumption
    }

def set_plug(device, status):
    pass