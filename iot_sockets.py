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

        device_id = self.message.get('id', None)
        device_token = self.message.get('token', None)
        if device_id is None or device_token is None:
            self.wfile.write(json.dumps(
                {'error': 'request must have id and token'}))
            return
        device = iot_db.Devices.query.get(device_id)
        if device.id is None:
            self.wfile.write(json.dumps(
                {'error': 'request id does not exist in the database'}))
            return
        if device_token != device.token:
            self.wfile.write(json.dumps(
                {'error': 'request token and actual token do not match'}))
            return
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


class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(1024)
        cur_thread = threading.current_thread()
        response = "{}: {}".format(cur_thread.name, data)
        self.request.sendall(response)

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

def client(ip, port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    try:
        sock.sendall(message)
        response = sock.recv(1024)
        print "Received: {}".format(response)
    finally:
        sock.close()


def start_device_server(port):
    HOST, PORT = "0.0.0.0", 8090
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = server.server_address
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

