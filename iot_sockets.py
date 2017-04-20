import socket
import SocketServer
import threading
import json
import iot_db
from datetime import datetime

# utility functions
# -----------------------
def err(message):
    return json.dumps({'error': str(message)})

def info(message):
    return json.dumps({'info': str(message)})

# remove ip address and port from db
def remove_conn(device_id):
    from IOTApp import app
    with app.app_context():
        device = iot_db.Devices.query.get(device_id)
        device.ip_address = None
        device.port = None
        iot_db.update_db()

# device actions
# --------------
# constantly recieved, keeps the socket open
def keepalive(device_id, current_consumption=None):
    from IOTApp import app
    # update current_consumption in the db
    if current_consumption != None:
        with app.app_context():
            device = iot_db.Devices.query.get(device_id)
            device.current_consumption = current_consumption
            iot_db.update_db()
    return False, None

# closes the connection safely
def disconnect(device_id):
    e = remove_conn(device_id)
    if e is not None:
        return True, {'error': str(e)}
    return True, {'info': 'connection closed (disconnect)'}

# returns the text sent in uppercase
# TODO: remove, for debugging
def echo_text(device_id, text):
    return False, {'echo': str(text).upper()}

# connection handler
# ------------------
class DeviceTCPHandler(SocketServer.StreamRequestHandler, object):
    # currently supported client actions
    actions = {
        'keepalive': keepalive,
        'disconnect': disconnect,
        'echo': echo_text,
    }

    def setup(self):
        # import app for the app_context()
        # see flask docs
        from IOTApp import app
        self.device_id = None
        
        super(DeviceTCPHandler, self).setup()
        # read PROXY v1 info
        # see http://www.haproxy.org/download/1.8/doc/proxy-protocol.txt
        data = ''
        try:
            data = self.rfile.readline().strip()
        except socket.timeout:
            return

        proxy_data = data.split()
        if proxy_data[0] != 'PROXY':
            # invalid proxy header
            return

        client_ip = proxy_data[2]
        client_port = int(proxy_data[4]) 

        # check id and token
        # ------------------
        # connection closed after 30 seconds of no activity
        self.request.settimeout(30)
        
        # read data, catching socket timeout exception
        data = ''
        try:
            data = self.rfile.readline().strip()
        except socket.timeout:
            return
        
        # load the json into an obj, catching parse errors
        message = {}
        try:
            message = json.loads(data)
        except:
            self.wfile.write(err('problem parsing JSON'))
            return

        # check the inital json contains an id and token
        device_id = message.get('id', None)
        device_token = message.get('token', None)
        if device_id is None or device_token is None:
            self.wfile.write(err('request must have id and token'))
            return
        
        # using the flask app context to manipulate the database
        with app.app_context():
            device = None
            try:
                device = iot_db.Devices.query.get(device_id)
            except Exception as e:
                self.wfile.write(err(str(e)))
                return                
            if device is None:
                self.wfile.write(err('invalid device id'))
                return
            if device_token != device.token:
                self.wfile.write(err('invalid device token'))
                return

            # update the database with the new data
            device.last_checked = datetime.utcnow()
            device.ip_address = client_ip
            device.port = client_port
            iot_db.update_db()

        self.device_id = device_id
        self.wfile.write(info('successfully authenticated'))

    # runs after setup
    def handle(self):
        from IOTApp import app

        if self.device_id is None:
            return

        # connection stays open
        # ---------------------
        while True:
            # read data, catching socket timeout exception
            data = ''
            try:
                data = self.rfile.readline()
            except socket.timeout:
                e = remove_conn(device_id)
                if e is not None:
                    self.wfile.write(err(str(e)))
                else:
                    self.wfile.write(info('connection closed (timeout)'))
                return
            
            # at this point data has been recieved
            # update last checked time 
            with app.app_context():
                device = None
                try:
                    device = iot_db.Devices.query.get(device_id)
                except Exception as e:
                    self.wfile.write(err(str(e)))
                    return
                device.last_checked = datetime.utcnow()
                iot_db.update_db()
            
            # parse json
            message = {}
            try:
                message = json.loads(data)
            except:
                self.wfile.write(err('problem parsing JSON'))
                return
            
            # check that 'action' key exists and is valid 
            action = message.get('action', None)
            if action is None:
                self.wfile.write(err('problem parsing JSON - no action'))
                return
            if action not in self.actions:
                self.wfile.write(err("no action '%s'" % action))
                return
            
            # get k(ey)w(ord) arg(uments)s
            # can be empty, dependent on action function
            kwargs = message.get('args', {})

            try:
                # call action with device_id and kwargs
                # return whether to close connection and message (can be None)
                end_con, resp = self.actions[action](device_id, **kwargs)
                if resp is not None:
                    self.wfile.write(json.dumps(resp))
                if end_con:
                    return 
            except Exception as e:
                # write the message of any error out and disconnect
                # TODO: remove, for debugging
                self.wfile.write(err(str(e)))
                return

    def finish(self):
        super(DeviceTCPHandler, self).finish()
        if self.device_id != None:
            remove_conn(self.device_id)


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_address, RequestHandlerClass):
        self.allow_reuse_address = True
        SocketServer.TCPServer.__init__(self,
                                        server_address,
                                        RequestHandlerClass)

def start_server():
    dev_server = ThreadedTCPServer(('127.0.0.1', 7070), DeviceTCPHandler)
    server_thread = threading.Thread(target=dev_server.serve_forever)
    server_thread.setDaemon(True)
    server_thread.start()