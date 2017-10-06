# ngtitov_peers.py
# Import Python's libraries
import platform
import datetime
from socket import *
from random import randint

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
RS_REQUESTS = ['REGISTER', 'LEAVE', 'PQUERY', 'KEEPALIVE', 'RFCQUERY']
SERVER_IP = 'localhost'
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
PROTOCOL_OS = 'OS: {}\n'
PROTOCOL_DATE = 'Date: {}\n'
PROTOCOL_EOP = 'EOP'
# Generate a random port number to which RFC server of this peer is listening
# Ports must be in the range [65400-65500] since VCL/EOS blocks all other ports
RFC_PORT = randint(65400, 65500)


def encapsulate_data_protocol(index=None):
    if request in RS_REQUESTS:
        _header = RS_PROTOCOL_HEADER.format(request)
    else:
        if request == 'RFCQUERY':
            _header = RFC_QUERY_HEADER
        elif request == 'GETRFC':
            _header = GET_RFC_HEADER.format(index)
        else:
            _header = ''
    _host = PROTOCOL_RFC_HOST_SERVER.format(rfc_host_server)
    _port = PROTOCOL_RFC_PORT_SERVER.format(rfc_port_server)
    _os = PROTOCOL_OS.format(platform.platform())
    _date = PROTOCOL_DATE.format(datetime.datetime.now())
    _protocol = _header + _host + _port + _os + _date + PROTOCOL_EOP
    return _protocol

# Create a TCP server welcoming socket and bind it to a well-known port
rfc_socket = socket(AF_INET, SOCK_STREAM)
try:
    rfc_socket.bind(('', RFC_PORT))
    # Server begins listening for incoming TCP requests from other peers
    rfc_socket.listen(1)
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
    def __init__(self):
        pass

    # Create TCP client socket for server on well-known port and initiate
    # connection with the Register Server
    @staticmethod
    def send_request():
        client_socket = socket(AF_INET, SOCK_STREAM)
        rs_response_message = None
        try:
            client_socket.connect((SERVER_IP, SERVER_PORT))
            rs_request_message = encapsulate_data_protocol()
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
        client_socket.close()
        del client_socket
        return

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
            pass
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
    else:
        print 'Command not found. Use \'help\' to see proper commands.\n'
