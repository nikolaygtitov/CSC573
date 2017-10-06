# ngtitov_registration_server.py
# Import Python's libraries
import datetime
import time
from socket import *


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
# The Application Layer Protocol for *-to-peer communication of P2P-DI/1.0 is
# defined as follows:
'''
---------------------------------------------------
 Protocol name and version | Status Code | Phrase |
---------------------------------------------------
 Header Field name:        |       Value          |
---------------------------------------------------
 Header Field name:        |       Value          |
---------------------------------------------------
           ...             |        ...           |
---------------------------------------------------
 EOP (End of Protocol)                            |
---------------------------------------------------
'''

# Initialization of constants
SERVER_PORT = 65423
TTL = 7200
THIRTY_DAYS = 2592000
PROTOCOL = 'P2P-DI/1.0'
STATUS_CODE_PHRASE = ' {} {}'
PROTOCOL_COOKIE = 'COOKIE: {}'
PROTOCOL_ACTIVE_PEER = 'Host: {} Port: {}'
PROTOCOL_EOP = 'EOP'


dict_peers = {}


def extract_data_protocol():
    _data_list = received_data.decode().split()
    _method = _data_list[0]
    _version = _data_list[1]
    try:
        assert _version == PROTOCOL, 'Undefined App Layer Protocol.. Exit'
    except AssertionError, _e:
        exit(_e)
    _host = _data_list[_data_list.index('Host:') + 1]
    _port = _data_list[_data_list.index('Port:') + 1]
    return _method, _host, _port


def encapsulate_data_protocol():
    _header = PROTOCOL + STATUS_CODE_PHRASE.format(status_code, phrase) + '\n'
    _protocol = _header
    if method in ['REGISTER', 'KEEPALIVE']:
        if status_code in [200, 201]:
            _protocol = _protocol + PROTOCOL_COOKIE.format(cookie) +  \
                        PROTOCOL_EOP
        else:
            _protocol = _protocol + PROTOCOL_EOP
    elif method == 'PQUERY':
        if status_code == 200:
            for _host, _port in dict_active_peers.iteritems():
                _protocol += _protocol + PROTOCOL_ACTIVE_PEER.format(
                    _host.hostname, _host.port)
    _protocol = _protocol + PROTOCOL_EOP
    return _protocol


def get_cookie():
    for _cookie, _peer in dict_peers.iteritems():
        if _peer.hostname == host:
            try:
                assert _cookie == _peer.cookie, \
                    'Cookie for peer {} does not match!'.format(host)
                return _cookie
            except AssertionError, _e:
                print _e
    return None


def execute_request():
    try:
        if method == 'REGISTER':
            if cookie is None:
                peer = Peer(host, len(dict_peers), True, port,
                            datetime.datetime.now())
                dict_peers[len(dict_peers)] = peer
                return 201, 'Created', None
            else:
                peer = dict_peers.get(cookie)
                peer.register_update(port)
                return 200, 'OK', None
        elif method == 'LEAVE':
            peer = dict_peers.get(cookie)
            peer.leave_update()
            return 200, 'OK', None
        elif method == 'PQUERY':
            if cookie is None:
                return 403, 'Forbidden [Peer is not register with the RS]', None
            else:
                peer = dict_peers.get(cookie)
                peer.update()
                _dict_active_peers = {}
                for _key, _peer in dict_peers.iteritems():
                    if _peer.flag and cookie != _peer.cookie:
                        _dict_active_peers[_peer.hostname] = _peer.port
                if len(_dict_active_peers) > 0:
                    return 200, 'OK', _dict_active_peers
                else:
                    return 404, 'Not Found [No other active peers in the ' \
                                'P2P-DI system found]', None
        elif method == 'KEEPALIVE':
            peer = dict_peers.get(cookie)
            peer.update()
            return 200, 'OK', None
        else:
            pass
        return '400 Bad Request', None
    except Exception as _e:
        print _e.__doc__
        print type(_e).__name__
        print _e.message
        return 404, 'Not Found', None


def do_show():
    for _key, _peer in dict_peers.iteritems():
        _peer.is_active()
        print _key, ' ==> ', 'Hostname: {} '.format(_peer.hostname), \
            'Cookie: {} '.format(_peer.cookie), 'Flag: {} '.format(
            _peer.flag), \
            'TTL: {} '.format(_peer.ttl), 'Port: {} '.format(_peer.port), \
            'Most Recent Registration Date: {} '.format(_peer.reg_date), \
            'Times host been registered for last 30 days: {} '.format(len(
                _peer.reg_times))


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
        self.update()
        self.port = _port
        _reg_time = time.time()
        self.reg_times.append(_reg_time)

    def leave_update(self):
            self.flag = False
            self.ttl = 0
            self.port = None

    def update(self):
        self.flag = True
        self.ttl = TTL
        _reg_time = time.time()
        for reg_time in self.reg_times:
            if _reg_time - reg_time > THIRTY_DAYS:
                self.reg_times.remove(reg_time)
            else:
                return

    def is_active(self):
        if self.flag:
            _time = time.time() - self.reg_times[-1]
            self.ttl = self.ttl - _time
            self.flag = True if self.ttl > 0 else False
            if not self.flag:
                self.ttl = 0


# Create a TCP server welcoming socket and bind it to a well-known port
server_socket = socket(AF_INET, SOCK_STREAM)
try:
    server_socket.bind(('', SERVER_PORT))
    # Server begins listening for incoming TCP requests from the peers by
    # queueing up as many as 5 connect requests
    server_socket.listen(5)
    print 'The Registration Server is ready to register...'
except error, (value, message):
    print 'Exception while opening and binding server TCP welcoming socket:'
    server_socket.close()
    del server_socket
    exit(message)

# Loop forever waiting for new connections from different peers
while True:
    # Wait on accept and create new socket
    connection_socket, address = server_socket.accept()
    # Read peer's request data from socket
    received_data = connection_socket.recv(1024)
    try:
        assert PROTOCOL_EOP in received_data.decode(), \
            'Did not receive all the data yet.. Wait..'
    except AssertionError, e:
        print e
        while PROTOCOL_EOP not in received_data.decode():
            received_data += connection_socket.recv(1024)
    print received_data.decode()
    method, host, port = extract_data_protocol()
    cookie = get_cookie()
    status_code, phrase, dict_active_peers = execute_request()
    response_message = encapsulate_data_protocol()
    connection_socket.send(response_message.encode())
    connection_socket.close()
    del connection_socket
    do_show()
