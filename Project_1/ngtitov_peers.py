# ngtitov_peers.py
# Import Python's libraries
import platform
import datetime
import threading
import re
import os
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
# Register Server IP needs to be updated accordingly
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
PROTOCOL_COOKIE = 'Cookie: {}\n'
PROTOCOL_OS = 'OS: {}\n'
PROTOCOL_DATE = 'Date: {}\n'
PROTOCOL_EOP = 'EOP'
TTL = 7200
HELP = 'Command not found. Use \'help\' to see proper commands.\n'
# Generate a random port number to which RFC server of this peer is listening
# Ports must be in the range [65400-65500] since VCL/EOS blocks all other ports
RFC_PORT = randint(65400, 65500)


file_space = raw_input('> Please specify YOUR own file space: ')
while not os.path.isdir(file_space):
    if file_space.upper() == 'EXIT':
        exit()
    print file_space + ': No such file or directory'
    file_space = raw_input('> Please specify YOUR own file space: ')

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


class RfcServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        # Loop forever waiting for new connections from different peers
        while True:
            # Wait on accept and create new socket
            try:
                connection_socket, address = rfc_socket.accept()
            except error:
                print 'Shuts down the RFC server welcoming socket...'
                exit()
            # Read peer's request data from socket
            request_data = connection_socket.recv(1024)
            try:
                assert PROTOCOL_EOP in request_data.decode(), \
                    'Did not receive all the data yet.. Wait..'
            except AssertionError, _e:
                print _e
                while PROTOCOL_EOP not in request_data.decode():
                    request_data += connection_socket.recv(1024)
            print request_data.decode()
            # response_message = extract_data_protocol(received_data.decode())
            # connection_socket.send(response_message.encode())
            # connection_socket.close()
            # del connection_socket


class RfcIndex:
    def __init__(self, index, title, hostname=rfc_host_server, ttl=TTL):
        self.index = index
        self.title = title
        self.hostname = hostname
        self.ttl = ttl


def update():
    rfcs = os.listdir(file_space)
    if rfcs:
        for rfc in rfcs:
            index = int(re.search(r'\d+', rfc).group())
            if index not in local_rfcs:
                with open(file_space + '/' + rfc, 'r') as rfc_file:
                    lines = rfc_file.read().splitlines()
                    title = ''
                    for i in range(len(lines)):
                        if lines[i] == 'Abstract':
                            title_split = 2
                            while lines[i - title_split]:
                                title = lines[i - title_split].lstrip() + title
                                title_split += 1
                    rfc_index = RfcIndex(index, title)
                    local_rfcs[index] = rfc_index


def do_show_rfc():
    if local_rfcs:
        print 'RFCs stored in the directory: \'{}\''.format(file_space)
        for index, rfc_index in local_rfcs.iteritems():
            print 'Index: {} '.format(rfc_index.index), \
                'Title: \'{}\' '.format(rfc_index.title), \
                'Hostname: {} '.format(rfc_index.hostname), \
                'TTL: {}'.format(rfc_index.ttl)
    else:
        print 'No RFCs are found in the directory \'{}\''.format(file_space)


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
            print 'Exception: Creating TCP socket and connecting to ' \
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


def extract_rs_response_data_protocol(response):
    response_list = response.split()
    version = response_list[0]
    try:
        assert version == PROTOCOL, 'Exception: Undefined App Layer Protocol...'
    except AssertionError, _e:
        print _e
        return None
    status_code = int(response_list[1])
    if status_code in [200, 201]:
        if not register_server.cookie:
            register_server.cookie = response_list[response_list.index(
                'Cookie:') + 1]
    elif status_code == 302:
        hosts = [response_list[i + 1] for i in range(len(response_list)) if
                 response_list[i] == 'Host:']
        ports = [response_list[i + 1] for i in range(len(response_list)) if
                 response_list[i] == 'Port:']
        try:
            assert len(hosts) == len(ports), \
                'Number of active hosts IP addresses: \'{}\' does not match ' \
                'the corresponding number of their ports: \'{}\' return from ' \
                'the Register Server \'{}\''.format(len(hosts), len(ports),
                                                    SERVER_IP)
        except AssertionError, _e:
            print _e
            return None
        dict_active_peers = dict(zip(hosts, ports))
        return dict_active_peers
    return None


def encapsulate_rs_request_data_protocol():
    header = RS_PROTOCOL_HEADER.format(request)
    host = PROTOCOL_RFC_HOST_SERVER.format(rfc_host_server)
    port = PROTOCOL_RFC_PORT_SERVER.format(rfc_port_server)
    cookie = PROTOCOL_COOKIE.format(register_server.cookie)
    _os_ = PROTOCOL_OS.format(platform.platform())
    date = PROTOCOL_DATE.format(datetime.datetime.now())
    protocol = header + host + port + cookie + _os_ + date + PROTOCOL_EOP
    return protocol


def do_show_peer():
    if register_server.dict_active_peers is None:
        print 'Not Found [No other active peers in the P2P-DI system found]'
        print 'Please update list of active peers with \'pquery\' commnand'
    else:
        for host, port in register_server.dict_active_peers.iteritems():
            print 'Host: {}, Port: {}'.format(host, port)


# Create and start new thread that takes care of RFC local server. All other
# peer's requests coming to welcoming port of this RFC server.
rfc_server_thread = RfcServer()
rfc_server_thread.start()

local_rfcs = {}
register_server = RegisterServer()
update()


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
            update()
        elif request == 'HELP':
            try:
                with open('help_peers.txt', 'r') as fin:
                    print fin.read()
            except Exception as e:
                print e.__doc__
                print type(e).__name__
                print e.message
        elif request == 'EXIT':
            print 'Stopping RFC Server...'
            rfc_socket.shutdown(SHUT_RD)
            rfc_socket.close()
            del rfc_socket
            rfc_server_thread.join()
            exit('Goodbye')
        elif request == '':
            pass
        else:
            print HELP
    elif len(command_fields) == 2:
        if request == 'GETRFC':
            pass
        elif request == 'SHOW':
            if command_fields[1] == 'PEER':
                do_show_peer()
            elif command_fields[1] == 'RFC':
                do_show_rfc()
            else:
                print 'usage: show arg: peer, rfc'
        else:
            print HELP
    else:
        print HELP
