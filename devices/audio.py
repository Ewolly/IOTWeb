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
    if (device.client_id is not None):
        return_dict.append({
            'client_id': device.client_id,
            'client_name': device.client.friendly_name,
            'ip_address': device.ip_address,
            'port': device.port
        })

    return return_dict