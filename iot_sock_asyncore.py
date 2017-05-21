import asyncore
import json
import iot_db
from datetime import datetime
from Queue import Queue

# -----------------
# utility functions
# -----------------
def err(message):
    return json.dumps({'error': str(message)})

def info(message):
    return json.dumps({'info': str(message)})

# --------------
# device actions
# --------------
# constantly received, keeps the socket open
def keepalive(device, current_consumption=None):
    from IOTApp import app
    # update current_consumption in the db
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

# ---------------
# server handlers
# ---------------
class DeviceTCPServer(asyncore.dispatcher):
    """Establishes connections to devices.
    """
    def __init__(self, address):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.set_reuse_addr()
        self.listen(2)

    def handle_accept(self):
        client_info = self.accept()
        if client_info is None:
            return
        sock, _ = client_info
        sock.timeout = 10
        device = auth(sock)
        if device is not None:
            handler = DeviceTCPHandler(sock=sock, device=device)
        else:
            sock.shutdown()
            sock.close()

    def auth(self, sock):
        # read PROXY v1 info
        # see http://www.haproxy.org/download/1.8/doc/proxy-protocol.txt
        data = ''
        try:
            while (1):
                data += sock.recv(512)
                if '\r\n' in data:
                    break
        except socket.timeout:
            # no response
            return None
        if '\r\n' not in data:
            # socket closed
            return None
        
        proxy_str, data = data.split('\r\n', 1)
        proxy_info = proxy_str.split()[0]
        if proxy_info[0] != 'PROXY' or len(proxy_info) < 5:
            # not a valid PROXY v1 header
            return None

        client_ip = proxy_data[2]
        client_port = int(proxy_data[4])

        data = None
        try:
            if '\r\n' in data:
                break
            data += sock.recv(512)
        except socket.timeout:
            # no response
            return None
        if '\r\n' not in data:
            # socket closed
            return None
        message = {}
        try:
            message = json.loads(data.strip())
        except:
            # invalid JSON
            sock.sendall(err('problem parsing JSON'))
            return None
        device_id = message.get('id')
        device_token = message.get('token')
        if device_id is None or device_token is None:
            sock.sendall(err('request must have id and token'))
            return None

        device = None
        # import app for the app_context()
        # see flask docs
        from IOTApp import app
        with app.app_context():
            try:
                device = iot_db.Devices.query.get(device_id)
            except Exception as e:
                sock.sendall(err(str(e)))
                return None
            if device is None:
                sock.sendall(err('invalid device id'))
                return None
            if device_token != device.token:
                sock.sendall(err('invalid device token'))
                return None

            # update the database with the new data
            device.last_checked = datetime.utcnow()
            device.ip_address = client_ip
            device.port = client_port
            device.action_queue = Queue()
            iot_db.update_db()

        sock.sendall(info('successfully authenticated'))
        return device

class DeviceTCPHandler(asyncore.dispatcher):
    """Handles a single device connection.
    """

    # currently supported client actions
    actions = {
        'keepalive': keepalive,
        'disconnect': disconnect,
        'echo': echo_text,
    }

    def __init__(self, sock, chunk_size=4096, device=None)
        self.chunk_size = chunk_size
        asyncore.dispatcher.__init__(self, sock=sock)
        self.data_to_write = Queue()
        self.device = device
        self.expect_resp = None

    def writable(self):
        from IOTApp import app
        with app.app_context():
            aq_empty = self.device.action_queue.empty()
        return not (aq_empty and self.data_to_write.empty())

    def handle_write(self):
        from IOTApp import app
        with app.app_context():
            aq_empty = self.device.action_queue.empty()
        
        if not self.data_to_write.empty():
            data, close_sock = self.data_to_write.pop()
            sent = self.send(data[:self.chunk_size])
            if sent < len(data):
                remaining = data[sent:]
                self.data_to_write.put(remaining, close_sock)
                return
            if close_sock:
                self.handle_close()
        elif not aq_empty:
            with app.app_context():
                data, self.expect_resp = self.device.action_queue.get()
            sent = self.send(data[:self.chunk_size])
            if sent < len(data):
                remaining = data[sent:]
                self.data_to_write.put(remaining, False)
                return

    def handle_read(self):
        data = ''
        try:
            while (1):
                data += self.sock.recv(512)
                if '\r\n' in data:
                    break
        except socket.timeout:
            # no response
            if e is not None:
                self.sock.sendall(err(str(e)))
            else:
                self.sock.sendall(info('connection closed (timeout)'))
            self.handle_close()
            return

        if '\r\n' not in data:
            # socket closed
            self.handle_close()
            return

        # at this point data has been received
        # update last checked time 
        with app.app_context():
            self.device.last_checked = datetime.utcnow()
            iot_db.update_db()
        
        # parse json
        message = {}
        try:
            message = json.loads(data)
        except:
            self.sock.sendall(err('problem parsing JSON'))
            self.handle_close()
            return
            action = message.get('action', None)
        if action is None:
            self.sock.sendall(err('problem parsing JSON - no action'))
            self.handle_close()
            return
        if action not in self.actions:
            self.sock.sendall(err("no action '%s'" % action))
            self.handle_close()
            return

        # get k(ey)w(ord) arg(uments)s
        # can be empty, dependent on action function
        kwargs = message.get('args', {})
        try:
            # call action with device_id and kwargs
            # return whether to close connection and message (can be None)
            if self.expect_resp is not None:
                end_con, resp = self.actions[action](self.device, **kwargs)
                self.expect_resp = None
            else:
                end_con, resp = self.expect_resp(self.device, **kwargs)

            if resp is not None:
                self.data_to_write.put(json.dumps(resp), end_con)

        except Exception as e:
            # write the message of any error out and disconnect
            # TODO: remove, for debugging
            self.sock.sendall(err(str(e)))
            self.handle_close()
            return

    def handle_close(self):
        from IOTApp import app
        with app.app_context():
            self.device.ip_address = None
            self.device.port = None
            del self.device.action_queue
            iot_db.update_db()
        self.close()