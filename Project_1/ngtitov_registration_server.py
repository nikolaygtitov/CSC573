# ngtitov_registration_server.py
# Import Python's libraries
import datetime
import time
from socket import *

# The Application Layer Protocol for peer-to-RS REQUEST communication of
# P2P-DI/1.0 is defined as follows:
'''
--------------------------------------
 Method  | Protocol name and version |
--------------------------------------
 Host:   |           IPv4            |
--------------------------------------
 Port:   |          Integer          |
--------------------------------------
 Cookie: |          Integer          |
--------------------------------------
  OS:    |          System           |
--------------------------------------
 Date:   | Yr-Mo-Day Hr-Min-Sec-Msec |
--------------------------------------
 EOP (End of Protocol)               |
--------------------------------------
'''
# The Application Layer Protocol for peer-to-peer REQUEST communication of
# P2P-DI/1.0 is defined as follows:
'''
----------------------------------------------
 Method  | Index | Protocol name and version |
----------------------------------------------
 Host:   |               IPv4                |
----------------------------------------------
 Port:   |              Integer              |
----------------------------------------------
  OS:    |              System               |
----------------------------------------------
 Date:   | Year-Month-Day Hour-Min-Sec-Msec  |
----------------------------------------------
 EOP (End of Protocol)                       |
----------------------------------------------
'''
# The Application Layer Protocol for *-to-peer RESPONSE communication of
# P2P-DI/1.0 is defined as follows:
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
STATUS_CODE_PHRASE = ' {} {}\n'
PROTOCOL_COOKIE = 'Cookie: {}\n'
PROTOCOL_ACTIVE_PEERS = 'Host: {} Port: {}\n'
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
    _cookie = None if _data_list[_data_list.index('Cookie:') + 1] == 'None' \
        else int(_data_list[_data_list.index('Cookie:') + 1])
    return _method, _host, _port, _cookie


def encapsulate_data_protocol():
    _header = PROTOCOL + STATUS_CODE_PHRASE.format(status_code, phrase)
    _protocol = _header
    if method in ['REGISTER', 'KEEPALIVE'] and status_code in [200, 201]:
        if not cookie:
            _cookie = dict_peers.keys()[-1]
            _peer = dict_peers.get(_cookie)
            try:
                assert _peer.hostname == host, 'Exception due to raise ' \
                                               'condition'
            except AssertionError, _e:
                print _e
                _cookie = None
                for _c, _p in dict_peers.iteritems():
                    if _p.hostname == host:
                        _cookie = _p.cookie
                        break
            _protocol = _protocol + PROTOCOL_COOKIE.format(_cookie)
        else:
            _protocol = _protocol + PROTOCOL_COOKIE.format(cookie)
    elif method == 'PQUERY' and status_code == 302:
        _active_peers = ''
        for _host, _port in dict_active_peers.iteritems():
            _active_peers += PROTOCOL_ACTIVE_PEERS.format(_host, _port)
        _protocol = _protocol + _active_peers
    _protocol = _protocol + PROTOCOL_EOP
    return _protocol


def execute_request():
    try:
        if method == 'REGISTER':
            if cookie is None:
                assert len(dict_peers) not in dict_peers, \
                    'Error: Cookie for the new peer is in use.'
                peer = Peer(host, port, _cookie=len(dict_peers), _flag=True)
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
                return 403, 'Forbidden [Peer is NOT register with the RS]', None
            else:
                peer = dict_peers.get(cookie)
                peer.update()
                _dict_active_peers = {}
                for _key, _peer in dict_peers.iteritems():
                    if _peer.flag and cookie != _peer.cookie:
                        _dict_active_peers[_peer.hostname] = _peer.port
                if len(_dict_active_peers) > 0:
                    return 302, 'Found', _dict_active_peers
                else:
                    return 404, 'Not Found [No other active peers in the ' \
                                'P2P-DI system found]', None
        elif method == 'KEEPALIVE':
            peer = dict_peers.get(cookie)
            peer.update()
            return 200, 'OK', None
        else:
            pass
        return 400, 'Bad Request', None
    except Exception as _e:
        print _e.__doc__
        # print type(_e).__name__
        # print _e.message
        return 404, 'Not Found [Peer is NOT register with the RS]', None


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
    def __init__(self, _hostname, _port, _cookie, _flag=False):
        self.hostname = _hostname
        self.port = _port
        self.cookie = _cookie
        self.flag = _flag
        self.reg_date = datetime.datetime.now()
        self.ttl = TTL
        self.reg_times = [time.time()]

    def register_update(self, _port):
        self.update()
        self.port = _port
        self.reg_times.append(time.time())

    def leave_update(self):
        self.port = None
        self.flag = False
        self.ttl = 0

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
    method, host, port, cookie = extract_data_protocol()
    status_code, phrase, dict_active_peers = execute_request()
    response_message = encapsulate_data_protocol()
    connection_socket.send(response_message.encode())
    connection_socket.close()
    del connection_socket
    do_show()
