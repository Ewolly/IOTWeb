class Smartplug(object):
    name = 'smartplug'

    @staticmethod
    def device_details(device):
        return_dict = {'plug_status': device.plug_status}
        if (device.current_consumption is not None):
            return_dict['current_consumption'] = int(device.current_consumption)
        
        return return_dict

    @staticmethod
    def set_plug(device, status):
        pass