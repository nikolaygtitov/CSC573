# ngtitov_registration_server.py

# Import Python's libraries
import sys
from socket import *

# Initialization of constants
SERVER_PORT = 65423

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
    # Read peers data and request from socket
    received_data = connection_socket.recv(1024)
    print received_data.decode()
    connection_socket.send("OK 0".encode())
    connection_socket.close()
    del connection_socket
