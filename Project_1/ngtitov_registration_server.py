# ngtitov_registration_server.py
# The Application Layer Protocol for peer-to-RS communication of P2P-DI/1.0 is
# defined as follows:
'''
-------------------------------------
 Method | Protocol name and version |
-------------------------------------
 Host:  |           IPv4            |
-------------------------------------
 Port:  |           xxxxx           |
-------------------------------------
  OS:   |           System          |
-------------------------------------
 Date:  | Yr-Mo-Day Hr-Min-Sec-Msec |
-------------------------------------
 EOP (End of Protocol)              |
-------------------------------------
'''

# Import Python's libraries
import sys
import datetime
import time
from socket import *

# Initialization of constants
SERVER_PORT = 65423
TTL = 7200
THIRTY_DAYS = 2592000
PROTOCOL_EOP = 'EOP'


dict_peers = {}


def extract_data_protocol():
    _data_list = received_data.decode().split()
    _method = _data_list[0]
    _host = _data_list[_data_list.index('Host:') + 1]
    _port = _data_list[_data_list.index('Port:') + 1]
    return _method, _host, _port


def get_cookie():
    for _cookie, _peer in dict_peers.iteritems():
        if _peer.hostname == host:
            try:
                assert _cookie == _peer.cookie, \
                    'Cookie for peer {} does not match!'.format(host)
                return _cookie
            except AssertionError, _e:
                sys.exit(_e)
    return None


def execute_request():
    if method == 'REGISTER':
        if cookie is None:
            peer = Peer(host, len(dict_peers), True, port,
                        datetime.datetime.now())
            dict_peers[len(dict_peers)] = peer
        else:
            peer = dict_peers.get(cookie)
            peer.register_update(port)
    elif method == 'LEAVE':
        pass
    elif method == 'PQUERY':
        pass
    elif method == 'KEEPALIVE':
        pass
    else:
        pass


class Peer:
    def __init__(self, _hostname, _cookie, _flag, _port, _reg_date, _ttl=TTL):
        self.hostname = _hostname
        self.cookie = _cookie
        self.flag = _flag
        self.ttl = _ttl
        self.port = _port
        self.reg_date = _reg_date
        self.reg_times = [time.time()]

    def register_update(self, _port):
        self.flag = True
        self.ttl = TTL
        self.port = _port
        _reg_time = time.time()
        self.reg_times.append(_reg_time)
        for reg_time in self.reg_times:
            if _reg_time - reg_time > THIRTY_DAYS:
                self.reg_times.remove(reg_time)
            else:
                return
        return

    def update(self):
        _time = time.time() - self.reg_times[-1]
        self.ttl = self.ttl - _time
        self.flag = True if self.ttl > 0 else False
        return


# Create a TCP server welcoming socket and bind it to a well-known port
try:
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind(('', SERVER_PORT))
    # Server begins listening for incoming TCP requests from the peers by
    # queueing up as many as 5 connect requests
    server_socket.listen(5)
    print 'The Registration Server is ready to register...'
except error, (value, message):
    print 'Exception while opening and binding server TCP welcoming socket:'
    server_socket.close()
    del server_socket
    sys.exit(message)

# Loop forever waiting for new connections from different peers
while True:
    # Wait on accept and create new socket
    connection_socket, address = server_socket.accept()
    # Read peer's request data from socket
    received_data = connection_socket.recv(1024)
    try:
        assert PROTOCOL_EOP in received_data.decode(),\
            'Did not receive all the data yet.. Wait..'
    except AssertionError, e:
        print e
        while PROTOCOL_EOP not in received_data.decode():
            received_data += connection_socket.recv(1024)
    method, host, port = extract_data_protocol()
    cookie = get_cookie()
    execute_request()
    for x, y in dict_peers.iteritems():
        y.update()
        print x, ' ==> ', 'Hostname: {} '.format(y.hostname), \
            'Cookie: {} '.format(y.cookie), 'Flag: {} '.format(y.flag), \
            'TTL: {} '.format(y.ttl), 'Port: {} '.format(y.port), \
            'Most Recent Registration Date: {} '.format(y.reg_date), \
            'Times host been registered for last 30 days: {} '.format(len(
                y.reg_times))
    connection_socket.send("OK 0".encode())
    connection_socket.close()
    del connection_socket
