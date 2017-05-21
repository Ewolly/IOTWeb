from smartplug import Smartplug

class Audio(Smartplug):
    name = 'audio'

    @staticmethod
    def device_details(device):
        return_dict = Smartplug.device_details(device)
        return_dict['connected'] = device.client_id is not None
        return_dict['speaker_status'] = True
        return_dict['mic_status'] = False
        return_dict['speaker_VU'] = 20
        return_dict['mic_VU'] = 80

        if device.client_id is not None:
            return_dict['client_id'] = device.client_id
            return_dict['client_name'] = device.client.friendly_name
            return_dict['ip_address'] = device.ip_address
            return_dict['port'] = device.port

        return return_dict