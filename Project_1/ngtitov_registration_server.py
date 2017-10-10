# ngtitov_registration_server.py
# Import Python's libraries
import datetime
import time
import threading
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


# Dictionary of peers.
# Mapping: Cookie <-> Peer(IP, Port, Cookie, TTL, ...)
dict_peers = {}


class Peer:
    def __init__(self, hostname, port, cookie, flag=False):
        self.hostname = hostname
        self.port = port
        self.cookie = cookie
        self.flag = flag
        self.reg_date = datetime.datetime.now()
        self.ttl = TTL
        self.reg_times = [time.time()]

    def register_update(self, port):
        self.reg_times.append(time.time())
        self.reg_date = datetime.datetime.now()
        self.port = port
        self.update()

    def leave_update(self):
        self.port = None
        self.flag = False
        self.ttl = 0

    def update(self):
        self.flag = True
        self.reg_times[-1] = time.time()
        _reg_time = time.time()
        for reg_time in self.reg_times:
            if _reg_time - reg_time > THIRTY_DAYS:
                self.reg_times.remove(reg_time)
            else:
                return

    def is_active(self):
        if self.flag:
            _time = time.time() - self.reg_times[-1]
            self.ttl = TTL - _time
            self.flag = True if self.ttl > 0 else False
            if not self.flag:
                self.ttl = 0


class PeerRequests(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        # Loop forever waiting for new connections from different peers
        while True:
            # Wait on accept and create new socket
            try:
                connection_socket, address = server_socket.accept()
            except error:
                print 'Shuts down the TCP Register Server welcoming socket...'
                exit()
            # Read peer's request data from socket
            received_data = connection_socket.recv(1024)
            try:
                assert PROTOCOL_EOP in received_data.decode(), \
                    'Did not receive all the data yet.. Wait..'
            except AssertionError, _e:
                print _e
                while PROTOCOL_EOP not in received_data.decode():
                    received_data += connection_socket.recv(1024)
            print received_data.decode()
            response_message = extract_data_protocol(received_data.decode())
            connection_socket.send(response_message.encode())
            connection_socket.close()
            del connection_socket


def extract_data_protocol(received_data):
    data_list = received_data.split()
    method = data_list[0]
    version = data_list[1]
    try:
        assert version == PROTOCOL, 'Exception: Undefined App Layer Protocol..'
    except AssertionError, _e:
        print _e
        response_message = encapsulate_data_protocol(417,
                                                     'Expectation Failed')
        return response_message
    host = data_list[data_list.index('Host:') + 1]
    port = data_list[data_list.index('Port:') + 1]
    cookie = None if data_list[data_list.index('Cookie:') + 1] == 'None' \
        else int(data_list[data_list.index('Cookie:') + 1])
    response_message = execute_request(method, host, port, cookie)
    return response_message


def execute_request(method, host, port, cookie):
    try:
        if method == 'REGISTER':
            if cookie is None:
                assert len(dict_peers) not in dict_peers, \
                    'Error: Cookie for the new peer is in use.'
                peer = Peer(host, port, cookie=len(dict_peers), flag=True)
                dict_peers[len(dict_peers)] = peer
                response_message = encapsulate_data_protocol(
                    201, 'Created', cookie=peer.cookie)
            else:
                peer = dict_peers.get(cookie)
                peer.register_update(port)
                response_message = encapsulate_data_protocol(200, 'OK',
                                                             cookie=peer.cookie)
        elif method == 'LEAVE':
            peer = dict_peers.get(cookie)
            peer.leave_update()
            response_message = encapsulate_data_protocol(200, 'OK')
            return response_message
        elif method == 'PQUERY':
            if cookie is None:
                response_message = encapsulate_data_protocol(
                    403, 'Forbidden [Peer is NOT register with the RS]')
            else:
                peer = dict_peers.get(cookie)
                peer.update()
                dict_active_peers = {}
                for key, peer in dict_peers.iteritems():
                    if peer.flag and cookie != peer.cookie:
                        dict_active_peers[peer.hostname] = peer.port
                if len(dict_active_peers) > 0:
                    response_message = encapsulate_data_protocol(
                        302, 'Found',
                        dict_active_peers=dict_active_peers)
                else:
                    response_message = encapsulate_data_protocol(
                        404,
                        'Not Found [No other active peers in the P2P-DI '
                        'system found]')
        elif method == 'KEEPALIVE':
            peer = dict_peers.get(cookie)
            peer.update()
            response_message = encapsulate_data_protocol(200, 'OK',
                                                         cookie=peer.cookie)
        else:
            response_message = encapsulate_data_protocol(400, 'Bad Request')
        return response_message
    except Exception as _e:
        print _e.__doc__
        print type(_e).__name__
        print _e.message
        response_message = encapsulate_data_protocol(
            404, 'Not Found [Peer is NOT register with the RS]')
        return response_message


def encapsulate_data_protocol(status_code, phrase, cookie=None,
                              dict_active_peers=None):
    header = PROTOCOL + STATUS_CODE_PHRASE.format(status_code, phrase)
    protocol = header
    if status_code in [200, 201] and cookie is not None:
        protocol = protocol + PROTOCOL_COOKIE.format(cookie)
    elif status_code == 302:
        active_peers = ''
        for host, port in dict_active_peers.iteritems():
            active_peers += PROTOCOL_ACTIVE_PEERS.format(host, port)
        protocol = protocol + active_peers
    protocol = protocol + PROTOCOL_EOP
    return protocol


def do_show():
    if len(dict_peers) > 0:
        print 'Show: Each Registered Peer Information...'
        for key, peer in dict_peers.iteritems():
            peer.is_active()
            print key, ' ==> ', 'Hostname: {} '.format(peer.hostname), \
                'Port: {} (RFC Server) '.format(peer.port), \
                'Cookie: {} '.format(peer.cookie), \
                'Flag: {} '.format(peer.flag), \
                'TTL: {} '.format(peer.ttl), \
                'Most Recent Registration Date: {} '.format(peer.reg_date), \
                'Times host been registered for last 30 days: {} '.format(
                    len(peer.reg_times))
    else:
        print 'No Registered Peers are found'


# Create a TCP Register Server welcoming socket
server_socket = socket(AF_INET, SOCK_STREAM)
try:
    # Bind welcoming socket to a well-known port
    server_socket.bind(('', SERVER_PORT))
    # Server begins listening for incoming TCP requests from the
    # peers by queueing up as many as 5 connect requests
    server_socket.listen(5)
    print 'The Registration Server is ready to register...'
except error, (value, message):
    print 'Exception: while binding the server TCP welcoming socket...'
    print 'Register Server has stopped...'
    server_socket.close()
    del server_socket
    exit(message)

# Create and start new thread that takes care of the all peer's requests coming
# to welcoming port of the Register Server
peer_requests_thread = PeerRequests()
peer_requests_thread.start()

while True:
    command = raw_input('> ').upper()
    command_fields = command.split(' ')
    request = command_fields[0]
    if len(command_fields) == 1:
        if request == 'SHOW':
            do_show()
        elif request == 'EXIT':
            print 'Stopping Register Server...'
            server_socket.shutdown(SHUT_RD)
            server_socket.close()
            del server_socket
            time.sleep(1)
            exit('Goodbye')
        elif request == 'HELP':
            try:
                with open('help_registration_server.txt', 'r') as fin:
                    print fin.read()
            except Exception as e:
                print e.__doc__
                print type(e).__name__
                print e.message
        elif request == '':
            pass
        else:
            print 'Command not found. Use \'help\' to see proper commands.\n'
    else:
        print 'Command not found. Use \'help\' to see proper commands.\n'
