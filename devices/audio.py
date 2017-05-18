import smartplug
from smartplug import *

name = 'audio'

def device_details(device):
    return_dict = {
        'connected': device.client_id is not None,
        'speaker_status': True,
        'mic_status': False,
        'speaker_VU': 20,
        'mic_VU': 80
    }
    if device.client_id is not None:
        return_dict['client_id'] = device.client_id
        return_dict['client_name'] = device.client.friendly_name
        return_dict['ip_address'] = device.ip_address
        return_dict['port'] = device.port

    plug_dict = smartplug.device_details(device).copy()
    return_dict.update(plug_dict)
    return return_dict