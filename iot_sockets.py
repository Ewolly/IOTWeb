import SocketServer
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

        device_id = self.message.get('id', None)
        device_token = self.message.get('token', None)
        if device_id is None or device_token is None:
            self.wfile.write(json.dumps(
                {'error': 'request must have id and token'}))
            return
            device = iot_db.Devices.query.get(device_id)
    if device is None:

        if device_id != iot_db.device_id: # yes i know these wont work they are plce holders
            self.wfile.write(json.dumps(
                {'error': 'request id and actual id do not match'}))
            return
        if device_token != iot_db.token:
            self.wfile.write(json.dumps(
                {'error': 'request token and actual token do not match'}))
            return
        iot_db.last_checked = datetime.utcnow()
        iot_db.ip_address = self.client_address
        port
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

if __name__ == "__main__":
    HOST, PORT = "localhost", 8899
    SocketServer.TCPServer.allow_reuse_address = True
    server = SocketServer.TCPServer((HOST, PORT), DeviceTCPHandler)
    server.serve_forever()