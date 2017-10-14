from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.protocols.policies import TimeoutMixin
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor

from datetime import datetime
import threading
import json

import iot_db
# from devices.smartplug import Smartplug

device_sockets = {}

# TODO: move to appropriate places
# --------------
# device actions
# --------------
def keepalive(device_id, current_consumption=None, device_type=None):
    from IOTApp import app
    with app.app_context():
        device = iot_db.Devices.query.get(device_id)
        if current_consumption is not None:
            device.current_consumption = current_consumption
            iot_db.update_db()
        if device_type is not None:
            device.module_type = device_type
            if device_type == 4 and iot_db.Infrared.query.get(device_id) is None:
                iot_db.add_to_db(iot_db.Infrared(device_id))
            iot_db.update_db()
    return False, {'info': 'kept alive'}

# closes the connection safely
def disconnect(device_id):
    return True, {'info': 'connection closed (disconnect)'}

# ----------------
# device responses
# ----------------
def power_resp(device_id, plug_status):
    from IOTApp import app
    with app.app_context():
        device = iot_db.Devices.query.get(device_id)
        device.plug_status = plug_status
        iot_db.update_db()

def power_state(device_id):
    from IOTApp import app
    with app.app_context():
        device = iot_db.Devices.query.get(device_id)
        device.plug_status = False
        iot_db.update_db()

def infrared(device_id, feedback):
    from IOTApp import app
    with app.app_context():
        ir_dev = iot_db.Infrared.query.get(device_id)
        newlist = []
        for i, feed in enumerate(feedback):
            if ir_dev.feedback[i]["enabled"]:
                newlist.append({"enabled": True, "input": feed})
                if ir_dev.feedback[i].get("name") is not None:
                    newlist[i]["name"] = ir_dev.feedback[i]["name"]
            else:
                newlist.append({"enabled": False})
                if ir_dev.feedback[i].get("name") is not None:
                    newlist[i]["name"] = ir_dev.feedback[i]["name"]
        ir_dev.feedback = newlist
        iot_db.update_db()

def spi(device_id, command, response):
    from IOTApp import app
    with app.app_context():
        device = iot_db.Devices.query.get(device_id)
        # infrared
        if device.module_type == 4:
            ir_dev = iot_db.Infrared.query.get(device_id)
            # feedback
            if command == 0x03:
                newlist = []
                for i in range(4):
                    newlist.append({
                        "enabled": ir_dev.feedback[i]["enabled"], 
                        "input": response & (1 << (i+1)) > 0,
                        "name": ir_dev.feedback[i].get("name")
                    })
                ir_dev.feedback = newlist
            elif command == 0x02:
                ir_dev.learning = response & 0x01
        iot_db.update_db()
        
def server_setup(device_id, ip, port):
    from IOTApp import app
    with app.app_context():
        device = iot_db.Devices.query.get(device_id)
        device.connecting = 2
        device.local_ip = ip
        device.local_port = port
        iot_db.update_db()

def server_stopped(device_id):
    from IOTApp import app
    with app.app_context():
        device = iot_db.Devices.query.get(device_id)
        device.connecting = 0
        device.local_ip = None
        device.local_port = None
        device.client_id = None
        device.ip_address = None
        device.port = None
        iot_db.update_db()

def disconnect_device(device_id):
    from IOTApp import app
    with app.app_context():
        device = iot_db.Devices.query.get(device_id)
        device.connecting = 0
        device.local_ip = None
        device.local_port = None
        device.client_id = None
        device.ip_address = None
        device.port = None
        iot_db.update_db()

class DeviceHandler(LineReceiver, TimeoutMixin):
    actions = {
        'keepalive': keepalive,
        'disconnect': disconnect,
    }

    responses = {
        'power_state': power_state,
        'power': power_resp,
        'infrared': infrared,
        'spi': spi,
        'server_setup': server_setup,
        'server_stopped': server_stopped
    }

    def __init__(self, devices):
        self.devices = devices
        self.device_id = None
        self.client_ip = None
        self.client_port = None
        self.state = 'PROXY'
        self.callback = None

    # ----------------
    # protocol methods
    # ----------------
    def connectionMade(self):
        self.setTimeout(10)

    def connectionLost(self, reason):
        if self.device_id in self.devices:
            disconnect_device(self.device_id)
            del self.devices[self.device_id]


    def lineReceived(self, line):
        print "recv:", line
        if self.state == 'PROXY':
            self.handle_PROXY(line)
        elif self.state == 'AUTH':
            self.handle_AUTH(line)
        else:
            self.handle_MESSAGE(line)

    def timeoutConnection(self):
        print "timed out connection"
        if self.state != 'PROXY':
            self.sendLine(self.info('timed out'))
            self.transport.abortConnection()
        else:
            self.transport.abortConnection()
    
    # ---------------
    # utility methods
    # ---------------
    def err(self, message):
        return json.dumps({'error': str(message)})

    def info(self, message):
        return json.dumps({'info': str(message)})

    # --------------
    # input handling
    # --------------
    def handle_PROXY(self, line):
        """read PROXY v1 info
        see http://www.haproxy.org/download/1.8/doc/proxy-protocol.txt
        """
        proxy_data = line.split()
        if len(proxy_data) < 4 or proxy_data[0] != 'PROXY':
            self.transport.abortConnection()
            return

        self.client_ip = proxy_data[2]
        self.client_port = int(proxy_data[4])
        self.state = 'AUTH'

    def handle_AUTH(self, line):
        """check id and token
        """
        message = {}
        try:
            message = json.loads(line)
        except Exception as e:
            self.sendLine(self.err('problem parsing JSON: %s' % str(e)))
            self.transport.loseConnection()
            return

        self.device_id = message.get('id')
        device_token = message.get('token')
        device_type = message.get('device_type')
        if self.device_id is None or device_token is None or device_type is None:
            self.sendLine(self.err('request must have id and token'))
            self.transport.loseConnection()
            return
        # import app for the app_context()
        # see flask docs
        from IOTApp import app
        with app.app_context():
            try:
                device = iot_db.Devices.query.get(self.device_id)
            except Exception as e:
                self.sendLine(self.err(str(e)))
                self.transport.loseConnection()
                return
            if device is None:
                self.sendLine(self.err('invalid device id'))
                self.transport.loseConnection()
                return
            if device_token != device.token:
                self.sendLine(self.err('invalid device token'))
                self.transport.loseConnection()
                return
            device.module_type = device_type
            if device_type == 4 and iot_db.Infrared.query.get(device_id) is None:
                iot_db.add_to_db(iot_db.Infrared(device_id))
            device.last_checked = datetime.utcnow()
            device.ip_address = self.client_ip
            device.port = self.client_port
            iot_db.update_db()
        self.devices[self.device_id] = self
        self.sendLine(self.info('successfully authenticated'))
        self.state = 'MSG'

    def handle_MESSAGE(self, line):
        from IOTApp import app
        with app.app_context():
            device = iot_db.Devices.query.get(self.device_id)
            
        device.last_checked = datetime.utcnow()
        self.resetTimeout()
        with app.app_context():
            iot_db.update_db()
        
        message = {}
        try:
            message = json.loads(line)
        except Exception as e:
            self.sendLine(self.err('problem parsing JSON: %s' % str(e)))
            self.transport.loseConnection()
            return

        action = message.get('action', None)
        response = message.get('response', None)
        if action is not None:
            if action not in self.actions:
                self.sendLine(self.err("no action '%s'" % action))
                self.transport.loseConnection()
                return
            self.handle_ACTION(action, message.get('kwargs', {}))
        elif response is not None:
            if response not in self.responses:
                self.sendLine(self.err("no response '%s'" % response))
                self.transport.loseConnection()
                return
            self.handle_RESPONSE(response, message.get('kwargs', {}))
        else:
            self.sendLine(self.err('problem parsing JSON - no action'))
            self.transport.loseConnection()
            return

    def handle_ACTION(self, action, kwargs):
        try:
            # call action with device_id and kwargs
            # return whether to close connection and message (can be None)
            end_con, resp = self.actions[action](self.device_id, **kwargs)
            if resp is not None:
                self.sendLine(json.dumps(resp))
            if end_con:
                self.transport.loseConnection()
                return
        except Exception as e:
            # write the message of any error out and disconnect
            # TODO: remove, for debugging
            self.sendLine(self.err(str(e)))
            self.transport.loseConnection()
            return

    def handle_RESPONSE(self, response, kwargs):
        try:
            # call response with device_id and kwargs
            if kwargs == None:
                self.responses[response](self.device_id)
            else:
                self.responses[response](self.device_id, **kwargs)
        except Exception as e:
            # write the message of any error out and disconnect
            # TODO: remove, for debugging
            self.sendLine(self.err(str(e)))
            self.transport.loseConnection()
            return

    # ---------------
    # output handling
    # ---------------
    def send_message(self, message):
        try:
            self.sendLine(json.dumps(message))
        except Exception as e:
            # write the message of any error out and disconnect
            # TODO: remove, for debugging
            self.sendLine(self.err(str(e)))
            self.transport.loseConnection()
            return


class DeviceFactory(Factory):
    def __init__(self, devices):
        self.devices = devices

    def buildProtocol(self, addr):
        return DeviceHandler(self.devices)

def start_server():
    endpoint = TCP4ServerEndpoint(reactor, 7070, interface='127.0.0.1')
    d = endpoint.listen(DeviceFactory(device_sockets))
    server_thread = threading.Thread(target=reactor.run, 
        kwargs={'installSignalHandlers': 0})
    server_thread.setDaemon(True)
    server_thread.start()
