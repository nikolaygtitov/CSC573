# ngtitov_peers.py
# Import Python's libraries
import platform
import datetime
from socket import *
from random import randint

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
RS_REQUESTS = ['REGISTER', 'LEAVE', 'PQUERY', 'KEEPALIVE']
SERVER_IP = '172.22.176.159' # 'localhost'
SERVER_PORT = 65423
PROTOCOL = 'P2P-DI/1.0'
PROTOCOL_METHOD = '{} '
RS_PROTOCOL_HEADER = PROTOCOL_METHOD + PROTOCOL + '\n'
RFC_QUERY = 'GET RFC-Index '
RFC_QUERY_HEADER = RFC_QUERY + PROTOCOL + '\n'
GET_RFC = 'GET RFC {} '
GET_RFC_HEADER = GET_RFC + PROTOCOL + '\n'
PROTOCOL_RFC_HOST_SERVER = 'Host: {}\n'
PROTOCOL_RFC_PORT_SERVER = 'Port: {}\n'
PROTOCOL_COOKIE = 'Cookie: {}\n'
PROTOCOL_OS = 'OS: {}\n'
PROTOCOL_DATE = 'Date: {}\n'
PROTOCOL_EOP = 'EOP'
# Generate a random port number to which RFC server of this peer is listening
# Ports must be in the range [65400-65500] since VCL/EOS blocks all other ports
RFC_PORT = randint(65400, 65500)


def extract_rs_response_data_protocol(response):
    _response_list = response.split()
    _version = _response_list[0]
    try:
        assert _version == PROTOCOL, 'Undefined App Layer Protocol.. Exit'
    except AssertionError, _e:
        print _e
        return None
    _status_code = int(_response_list[1])
    if _status_code in [200, 201]:
        if not register_server.cookie:
            register_server.cookie = _response_list[_response_list.index(
                'Cookie:') + 1]
    elif _status_code == 302:
        _hosts = [_response_list[i + 1] for i in range(len(_response_list)) if
                  _response_list[i] == 'Host:']
        _ports = [_response_list[i + 1] for i in range(len(_response_list)) if
                  _response_list[i] == 'Port:']
        try:
            assert len(_hosts) == len(_ports), \
                'Number of active hosts IP addresses: \'{}\' does not match ' \
                'the corresponding number of their ports: \'{}\' return from ' \
                'the Register Server \'{}\''.format(len(_hosts), len(_ports),
                                                    SERVER_IP)
        except AssertionError, _e:
            print _e
            return None
        _dict_active_peers = dict(zip(_hosts, _ports))
        return _dict_active_peers
    return None


def encapsulate_rs_request_data_protocol():
    _header = RS_PROTOCOL_HEADER.format(request)
    _host = PROTOCOL_RFC_HOST_SERVER.format(rfc_host_server)
    _port = PROTOCOL_RFC_PORT_SERVER.format(rfc_port_server)
    _cookie = PROTOCOL_COOKIE.format(register_server.cookie)
    _os = PROTOCOL_OS.format(platform.platform())
    _date = PROTOCOL_DATE.format(datetime.datetime.now())
    _protocol = _header + _host + _port + _cookie + _os + _date + PROTOCOL_EOP
    return _protocol

# Create a TCP server welcoming socket and bind it to a well-known port
rfc_socket = socket(AF_INET, SOCK_STREAM)
try:
    rfc_socket.bind(('', RFC_PORT))
    # Server begins listening for incoming TCP requests from other peers
    rfc_socket.listen(5)
    print 'RFC server is initialized and listing ...'
except error, (value, message):
    print 'Exception while opening and binding RFC welcoming socket:'
    rfc_socket.close()
    del rfc_socket
    exit(message)

# Determine IP address and port number associated with the RFC server welcoming
# pocket
rfc_host_server = getaddrinfo(
    gethostname(), rfc_socket.getsockname()[1], AF_INET, SOCK_STREAM)[0][-1][0]
rfc_port_server = getaddrinfo(
    gethostname(), rfc_socket.getsockname()[1], AF_INET, SOCK_STREAM)[0][-1][1]
# RFC server port must be what was defined previously as random
try:
    assert rfc_port_server == RFC_PORT, 'RFC server port does not match'
except AssertionError, e:
    exit(e)


class RegisterServer:
    def __init__(self, cookie=None, dict_active_peers=None):
        self.cookie = cookie
        self.dict_active_peers = dict_active_peers

    # Create TCP client socket for server on well-known port and initiate
    # connection with the Register Server
    def send_request(self):
        client_socket = socket(AF_INET, SOCK_STREAM)
        rs_response_message = None
        try:
            client_socket.connect((SERVER_IP, SERVER_PORT))
            rs_request_message = encapsulate_rs_request_data_protocol()
            client_socket.send(rs_request_message.encode())
            rs_response_message = client_socket.recv(1024)
            assert PROTOCOL_EOP in rs_response_message, \
                'Did not receive the entire response yet.. Wait..'
        except AssertionError, _e:
            print _e
            while PROTOCOL_EOP not in rs_response_message.decode():
                rs_response_message += client_socket.recv(1024)
        except (error, herror, gaierror, timeout), (_value, _message):
            print 'Exception in creating TCP socket and connecting to ' \
                  'Register Server: {}'.format(SERVER_IP)
            print _message
            client_socket.close()
            del client_socket
            return
        print rs_response_message.decode()
        self.dict_active_peers = extract_rs_response_data_protocol(
            rs_response_message.decode())
        client_socket.close()
        del client_socket
        return

    def do_show_peer(self):
        if self.dict_active_peers is None:
            print 'Not Found [No other active peers in the P2P-DI system found]'
            print 'Please update list of active peers with \'pquery\' commnand'
        else:
            for _host, _port in self.dict_active_peers.iteritems():
                print 'Host: {}, Port: {}'.format(_host, _port)

register_server = RegisterServer()
while True:
    command = raw_input('> ').upper()
    command_fields = command.split(' ')
    request = command_fields[0]
    if len(command_fields) == 1:
        if request in RS_REQUESTS:
            register_server.send_request()
        elif request == 'GETRFC':
            print 'usage: getrfc number'
        elif request == 'SHOW':
            print 'usage: show arg: peer, rfc'
        elif request == 'UPDATE':
            pass
        elif request == 'HELP':
            try:
                with open('help_peers.txt', 'r') as fin:
                    print fin.read()
            except Exception as e:
                print e.__doc__
                print type(e).__name__
                print e.message
        elif request == 'EXIT':
            rfc_socket.close()
            del rfc_socket
            exit('Goodbye')
        elif request == '':
            pass
        else:
            print 'Command not found. Use \'help\' to see proper commands.\n'
    elif len(command_fields) == 2:
        if request == 'GETRFC':
            pass
        elif request == 'SHOW':
            if command_fields[1] == 'PEER':
                register_server.do_show_peer()
            elif command_fields[1] == 'RFC':
                pass
            else:
                'Command not found. Use \'help\' to see proper commands.\n'
        else:
            'Command not found. Use \'help\' to see proper commands.\n'
    else:
        print 'Command not found. Use \'help\' to see proper commands.\n'
