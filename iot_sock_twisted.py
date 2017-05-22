from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.protocols.policies import TimeoutMixin
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor

from datetime import datetime
import threading
import json
import iot_db

# TODO: move to appropriate places
# --------------
# device actions
# --------------
def keepalive(device, current_consumption=None):
    from IOTApp import app
    if current_consumption != None:
        with app.app_context():
            device.current_consumption = current_consumption
            iot_db.update_db()
    return False, None

# closes the connection safely
def disconnect(device):
    return True, {'info': 'connection closed (disconnect)'}

# returns the text sent in uppercase
# TODO: remove, for debugging
def echo_text(device, text):
    return False, {'echo': str(text).upper()}


class DeviceHandler(LineReceiver, TimeoutMixin):
    actions = {
        'keepalive': keepalive,
        'disconnect': disconnect,
        'echo': echo_text,
    }

    def __init__(self, devices):
        self.devices = devices
        self.device = None
        self.client_ip = None
        self.client_port = None
        self.state = 'PROXY'

    # ----------------
    # protocol methods
    # ----------------
    def connectionMade(self):
        self.setTimeout(10)

    def connectionLost(self, reason):
        if self.device in self.devices:
            # TODO: disconnect device
            del self.devices[self.device]

    def lineReceived(self, line):
        if self.state == 'PROXY':
            self.handle_PROXY(line)
        elif self.state == 'AUTH':
            self.handle_AUTH(line)
        else:
            self.handle_MESSAGE(line)

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

        device_id = message.get('id')
        device_token = message.get('token')
        if device_id is None or device_token is None:
            self.sendLine(self.err('request must have id and token'))
            self.transport.loseConnection()
            return
        # import app for the app_context()
        # see flask docs
        from IOTApp import app
        with app.app_context():
            try:
                self.device = iot_db.Devices.query.get(device_id)
            except Exception as e:
                self.sendLine(self.err(str(e)))
                self.transport.loseConnection()
                return                
            if self.device is None:
                self.sendLine(self.err('invalid device id'))
                self.transport.loseConnection()
                return
            if device_token != self.device.token:
                self.sendLine(self.err('invalid device token'))
                self.transport.loseConnection()
                return

            self.device.last_checked = datetime.utcnow()
            self.device.ip_address = self.client_ip
            self.device.port = self.client_port
            iot_db.update_db()
        self.devices[self.device] = self
        self.sendLine(self.info('successfully authenticated'))
        self.state = 'MSG'

    def handle_MESSAGE(line):
        with app.app_context():
            self.device.last_checked = datetime.utcnow()
            iot_db.update_db()
        
        message = {}
        try:
            message = json.loads(line)
        except Exception as e:
            self.sendLine(self.err('problem parsing JSON: %s' % str(e)))
            self.transport.loseConnection()
            return

        action = message.get('action', None)
        if action is None:
            self.sendLine(self.err('problem parsing JSON - no action'))
            self.transport.loseConnection()
            return
        if action not in self.actions:
            self.sendLine(self.err("no action '%s'" % action))
            self.transport.loseConnection()
            return

        kwargs = message.get('args', {})
        try:
            # call action with device_id and kwargs
            # return whether to close connection and message (can be None)
            end_con, resp = self.actions[action](self.device, **kwargs)
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

    def timeoutConnection(self):
        if self.state != 'PROXY':
            self.sendLine(self.info('timed out'))
            self.transport.loseConnection()
        else:
            self.transport.abortConnection()
            

class DeviceFactory(Factory):
    def __init__(self):
        self.devices = {}

    def buildProtocol(self, addr):
        return DeviceHandler(self.devices)

def start_server():
    endpoint = TCP4ServerEndpoint(reactor, 7070, interface='127.0.0.1')
    d = endpoint.listen(DeviceFactory())
    server_thread = threading.Thread(target=reactor.run, 
        kwargs={'installSignalHandlers': 0})
    server_thread.setDaemon(True)
    server_thread.start()
