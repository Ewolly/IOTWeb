import socket
import SocketServer
import threading
import json
import iot_db
from datetime import datetime

def keepalive():
    return False, None

def disconnect():
    return True, {'info': 'connection closed (disconnect)'}

def echo_text(text):
    return False, {'echo': str(text).upper()}

class DeviceTCPHandler(SocketServer.StreamRequestHandler):
    supported_actions = {
        'keepalive': keepalive,
        'disconnect': disconnect,
        'echo': echo_text,
    }

    def handle(self):
        from IOTApp import app
        with app.app_context():    
            self.request.settimeout(30)
            try:
                self.data = self.rfile.readline().strip()
            except:
                return
            
            self.message = None
            try:
                self.message = json.loads(self.data)
            except:
                self.wfile.write(json.dumps({'error': 'problem parsing JSON'}))
                return

            device_id = self.message.get('id', None)
            device_token = self.message.get('token', None)
            if device_id is None or device_token is None:
                self.wfile.write(json.dumps(
                    {'error': 'request must have id and token'}))
                return

            try:
                device = iot_db.Devices.query.get(device_id)
            except Exception as e:
                self.wfile.write(json.dumps({'error': repr(e)}))
                return
            if device is None:
                self.wfile.write(json.dumps(
                    {'error': 'request id does not exist in the database'}))
                return
            if device_token != device.token:
                self.wfile.write(json.dumps(
                    {'error': 'request token and actual token do not match'}))
                return

            device.last_checked = datetime.utcnow()
            device.ip_address = self.client_address[0]
            device.port = self.client_address[1]
            iot_db.update_db()

            self.wfile.write(json.dumps({'info': 'successfully authenticated'}))

            while True:
                try:
                    self.data = self.rfile.readline()
                except:
                    self.wfile.write(json.dumps({'info': 'connection closed (timeout)'}))
                    return

                device.last_checked = datetime.utcnow()
                try:
                    self.message = json.loads(self.data)
                except:
                    self.wfile.write(json.dumps({'error': 'problem parsing JSON'}))
                    return
                action = self.message.get('action', None)
                args = self.message.get('args', {})
                if action is None:
                    self.wfile.write(json.dumps({'error': 'problem parsing JSON - no action'}))
                    return

                if action not in self.supported_actions:
                    self.wfile.write(json.dumps({'error': "no action '%s'" % action}))
                    return

                self.end_conn = False
                self.response_obj = None
                try:
                    self.end_conn, self.response_obj = self.supported_actions[action](**args)
                except Exception as e:
                    self.wfile.write(json.dumps({'error': str(e)}))
                    return

                if self.response_obj is not None:
                    self.wfile.write(json.dumps(self.response_obj))
                if self.end_conn:
                    return 


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_address, RequestHandlerClass):
        self.allow_reuse_address = True
        SocketServer.TCPServer.__init__(self,
                                        server_address,
                                        RequestHandlerClass)

def start_server():
    dev_server = ThreadedTCPServer(('0.0.0.0', 7777), DeviceTCPHandler)
    server_thread = threading.Thread(target=dev_server.serve_forever)
    server_thread.setDaemon(True)
    server_thread.start()