# ngtitov_peers.py

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
import platform
import datetime
from socket import *
from random import randint

# Initialization of constants
SERVER_IP = 'localhost'
SERVER_PORT = 65423
PROTOCOL_METHOD = '{} ' + 'P2P-DI/1.0\n'
PROTOCOL_RFC_HOST_SERVER = 'Host: {}\n'
PROTOCOL_RFC_PORT_SERVER = 'Port: {}\n'
PROTOCOL_OS = 'OS: {}\n'
PROTOCOL_DATE = 'Date: {}\n'
PROTOCOL_EOP = 'EOP'
# Generate a random port number to which RFC server of this peer is listening
# Ports must be in the range [65400-65500] since VCL/EOS blocks all other ports
RFC_PORT = randint(65400, 65500)


def encapsulate_data_protocol(request):
    _method = PROTOCOL_METHOD.format(request)
    _rfc_host_server = PROTOCOL_RFC_HOST_SERVER.format(rfc_host_server)
    _rfc_port_server = PROTOCOL_RFC_PORT_SERVER.format(rfc_port_server)
    _os = PROTOCOL_OS.format(platform.platform())
    _date = PROTOCOL_DATE.format(datetime.datetime.now())
    _protocol = _method + _rfc_host_server + _rfc_port_server + _os + _date +\
        PROTOCOL_EOP
    return _protocol

# Create a TCP server welcoming socket and bind it to a well-known port
try:
    rfc_socket = socket(AF_INET, SOCK_STREAM)
    rfc_socket.bind(('', RFC_PORT))
    # Server begins listening for incoming TCP requests from other peers
    rfc_socket.listen(1)
    print 'RFC server is initialized and listing ...'
except error, (value, message):
    print 'Exception while opening and binding RFC welcoming socket:'
    rfc_socket.close()
    del rfc_socket
    sys.exit(message)

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
    sys.exit(e)


# Create TCP client socket for server on well-known port and initiate
# connection with the server
try:
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((SERVER_IP, SERVER_PORT))
    rs_request_message = encapsulate_data_protocol('REGISTER')
    client_socket.send(rs_request_message.encode())
    rs_response_message = client_socket.recv(1024)
    print rs_response_message.decode()
    client_socket.close()
    del client_socket
except (error, herror, gaierror, timeout), (value, message):
    print 'Exception in creating TCP socket and connecting to server: {' \
          '}'.format(SERVER_IP)
    client_socket.close()
    del client_socket
    sys.exit(message)
