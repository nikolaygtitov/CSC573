# ngtitov_peers.py

# Import Python's libraries
from socket import *
from random import randint

# Initialization of constants
SERVER_IP = 'localhost'
SERVER_PORT = 65423
PROTOCOL_REG = 'REGISTER PEER P2P-DI/1.0'
PROTOCOL_HOST = 'HOST: {}'
PROTOCOL_PORT = 'PORT: {}'
# Generate a random port number to which RFC server of this peer is listening
# Ports must be in the range [65400-65500] since VCL/EOS blocks all other ports
RFC_PORT = randint(65400, 65500)

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
rfc_ip_server = getaddrinfo(
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
    rs_request_message = PROTOCOL_REG + '\n' + PROTOCOL_HOST.format(
        rfc_ip_server) + '\n' + PROTOCOL_PORT.format(rfc_port_server)
    client_socket.send(rs_request_message.encode())
    rs_response_message = client_socket.recv(1024)
    print rs_request_message.decode()
    client_socket.close()
    del client_socket
except (error, herror, gaierror, timeout), (value, message):
    print 'Exception in creating TCP socket and connecting to server: {' \
          '}'.format(SERVER_IP)
    client_socket.close()
    del client_socket
    sys.exit(message)
