from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.protocols.policies import TimeoutMixin
from twisted.internet import reactor

import json
import iot_db

class DeviceHandler(LineReceiver, TimeoutMixin):
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
    def err(message):
        return json.dumps({'error': str(message)})

    def info(message):
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

        client_ip = proxy_data[2]
        client_port = int(proxy_data[4])
        self.state = 'PROXY'

    def handle_AUTH(self, line):
        """check id and token
        """
        message = {}
        try:
            message = json.loads(data)
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
            self.device.ip_address = client_ip
            self.device.port = client_port
            iot_db.update_db()
        self.devices[self.device] = self
        self.sendLine(self.info('successfully authenticated'))
        self.state = 'MSG'

    def handle_MESSAGE(line):
        # TODO: handle messages
        if line == 'disconnect':
            self.sendLine(self.info('goodbye'))
            self.transport.loseConnection()
        else:
            self.sendLine(self.info(line))

    def timeoutConnection(self):
        if state != 'PROXY':
            self.sendLine(self.info)
        self.transport.abortConnection()


class DeviceFactory(Factory):
    def __init__(self):
        self.devices = {}

    def buildProtocol(self, addr):
        return DeviceHandler(self.devices)

def start_server():
    reactor.listenTCP(7070, DeviceFactory())
    server_thread = threading.Thread(target=reactor.run)
    server_thread.setDaemon(True)
    server_thread.start()