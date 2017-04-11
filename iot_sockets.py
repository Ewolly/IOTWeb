import SocketServer
import json

class DeviceTCPHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(30)
        try:
            self.data = self.rfile.readline().strip()
        except:
            print "No initial connection."
            return
            # delete device
        if self.data == '':
            return
        
        print self.data
        self.message = None
        try:
            self.message = json.loads(self.data)
        except:
            self.wfile.write(json.dumps({'error': 'problem parsing JSON'}))
            return

        device_id = self.message.get('id', None)
        device_token = self.message.get('token', None)
        # if device_id is None or device_token is None:
        #     self.wfile.write(json.dumps(
        #         {'error': 'request must have id and token'}))
        #     self.shutdown()
        #     return

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
    SocketServer.TCPServer.timeout = 1
    server = SocketServer.TCPServer((HOST, PORT), DeviceTCPHandler)
    server.serve_forever()
