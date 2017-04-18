import socket
import SocketServer
import threading
import json
import iot_db
from datetime import datetime

class DeviceTCPHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(30)
        try:
            self.data = self.rfile.readline().strip()
        except:
            print "No initial connection."
            return
        if self.data == '':
            return
        
        self.message = None
        try:
            self.message = json.loads(self.data)
        except:
            self.wfile.write(json.dumps({'error': 'problem parsing JSON'}))
            return

        self.wfile.write(json.dumps(
                {'error': '1'}))

        device_id = self.message.get('id', None)
        device_token = self.message.get('token', None)
        if device_id is None or device_token is None:
            self.wfile.write(json.dumps(
                {'error': 'request must have id and token'}))
            return

        self.wfile.write(json.dumps(
                {'error': '2'}))

        device = iot_db.Devices.query.get(device_id)
        
        if device is None:
            self.wfile.write(json.dumps(
                {'error': 'request id does not exist in the database'}))
            return

        self.wfile.write(json.dumps(
            {'error': '3'}))

        if device_token != device.token:
            self.wfile.write(json.dumps(
                {'error': 'request token and actual token do not match'}))
            return

        self.wfile.write(json.dumps(
                {'error': '4'}))

        device.last_checked = datetime.utcnow()
        device.ip_address = self.client_address[0]
        port = self.client_address[1]
        iot_db.update_db()

        # print '{}\'s device "{}" connected from {}.'.format(
        #     device.user.email
        #     device.friendly_name,
        #     self.client_address[0])

        print '{}: {} ({})'.format(device_id, device_token, 
            self.client_address[0])
        
        while True:
            try:
                self.data = self.rfile.readline()
            except:
                print "Connection timed out."
                return

            if self.data == '':
                return
            self.wfile.write(self.data)


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

def start_device_server(port):
    SocketServer.TCPServer.allow_reuse_address = True
    HOST, PORT = "0.0.0.0", 8091
    server = ThreadedTCPServer((HOST, PORT), DeviceTCPHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

