"""
ngtitov_peers.py

CSC 573 (601) - Internet Protocols
This program implements the solution the Project 1 assignment: Peer-to-Peer
with Distributed Index (P2P-DI) System for Downloading RFCs.

This is Peer implementation that can communicate with Register Server and
other peers in the P2P-DI system. Each peer implements  3 (three) major
functionality:
- Each peer maintains an RFC index with information about RFCs it has
locally, as well  as RFCs maintained remotely by other peers it has recently
contacted.
- It also implements an RFC server that other peers may contact to download
desired RFCs.
- It also implements an RFC client that is used for connecting to the
Register Server and the RFC Server of remote peers.

The Application Layer Protocol of the P2P-DI system is designed for peers to
communicate with the Register Server and among themselves. Protocol details
are provided below.

@version: 1.0
@todo: None
@since: October 02, 2017

@status: Complete
@requires: help_peers.txt file

@contact: ngtitov@ncsu.edu
@author: Nikolay G. Titov
"""


# Import required Python libraries
import platform
import datetime
import threading
import re
import os
import time
from socket import *
from random import randint

# The Application Layer Protocol for peer-to-RS REQUEST communication of
# P2P-DI/1.0 is defined as follows:
"""
-------------------------------------------------
| Type    | Method | Protocol name and version  |
-------------------------------------------------
| Host:   |  IPv4  | Port: |      Integer       |
-------------------------------------------------
| Cookie: |               Integer               |
-------------------------------------------------
|  OS:    |               System                |
-------------------------------------------------
| Date:   |  Year-Month-Day Hour-Min-Sec-Msec   |
-------------------------------------------------
|            EOP (End of Protocol)              |
-------------------------------------------------
"""

# The Application Layer Protocol for peer-to-peer REQUEST communication of
# P2P-DI/1.0 is defined as follows:
"""
-----------------------------------------------------------------
| Type  | Method | Index (optional) | Protocol name and version |
-----------------------------------------------------------------
| Host: |  IPv4  |       Port:      |          Integer          |
-----------------------------------------------------------------
|  OS:  |                       System                          |
-----------------------------------------------------------------
| Date: |         Year-Month-Day Hour-Min-Sec-Msec              |
-----------------------------------------------------------------
|                  EOP (End of Protocol)                        |
-----------------------------------------------------------------
"""

# The Application Layer Protocol for RS-to-peer RESPONSE communication of
# P2P-DI/1.0 is defined as follows:
"""
-----------------------------------------------------
| Protocol name and version | Status Code | Phrase  |
-----------------------------------------------------
|    Cookie: (optional)     |        Integer        |
-----------------------------------------------------
|   Host:   |      IPv4     |    Port:    | Integer |
-----------------------------------------------------
|   Host:   |      IPv4     |    Port:    | Integer |
-----------------------------------------------------
|    ...    |       ...     |     ...     |   ...   |
-----------------------------------------------------
|                EOP (End of Protocol)              |
-----------------------------------------------------
"""

# The Application Layer Protocol for peer-to-peer in RESPONSE communication of
# RFCQuery request of P2P-DI/1.0 is defined as follows:
"""
-----------------------------------------------------------------------
| Protocol name and version |        Status Code       |    Phrase    |
-----------------------------------------------------------------------
| Index: | Integer | Title: | String | Size: | Integer | Host: | IPv4 |
-----------------------------------------------------------------------
| Index: | Integer | Title: | String | Size: | Integer | Host: | IPv4 |
-----------------------------------------------------------------------
|  ...   |   ...   |  ...   |  ...   |  ...  |   ...   |  ...  | ...  |
-----------------------------------------------------------------------
|                        EOP (End of Protocol)                        |
-----------------------------------------------------------------------
"""

# The Application Layer Protocol for peer-to-peer in RESPONSE communication of
# Get RFC request of the P2P-DI/1.0 is defined as follows. Note that header
# protocol comes as plane text, but the requested RFC in the binary mode:
"""
-----------------------------------------------------
| Protocol name and version | Status Code | Phrase  |
-----------------------------------------------------
|           Size:           |        Integer        |
-----------------------------------------------------
|                EOP (End of Protocol)              |
-----------------------------------------------------
              Wait for Accepting message
-----------------------------------------------------
|                                                   |
|                        RFC                        |
|                   (Binary Mode)                   |
|                                                   |
-----------------------------------------------------
"""

# Initialization of constants
# Note: Register Server IP needs to be updated accordingly by default it is
# localhost
SERVER_IP = '127.0.0.1'
RS_REQUESTS = ['REGISTER', 'LEAVE', 'PQUERY', 'KEEPALIVE']
SERVER_PORT = 65423
PROTOCOL = 'P2P-DI/1.0'
RS_PROTOCOL_HEADER = '{} {} P2P-DI/1.0\n'
GET_RFC_QUERY_HEADER = 'GET RFC-INDEX P2P-DI/1.0\n'
GET_RFC_HEADER = 'GET RFC {} P2P-DI/1.0\n'
PEER_RESPONSE_HEADER = 'P2P-DI/1.0 {} {}\n'
PROTOCOL_HOST_PORT = 'Host: {} Port: {}\n'
PROTOCOL_RFC_INDEX = 'Index: {} Title: <start> {} <end> Size: {} Host: {}\n'
PROTOCOL_COOKIE = 'Cookie: {}\n'
PROTOCOL_OS = 'OS: {}\n'
PROTOCOL_DATE = 'Date: {}\n'
PROTOCOL_EOP = 'EOP'
RFC_FILE = '{}/rfc{}.txt'
TTL = 7200
MAX_BUFFER_SIZE = 1024
# Generate a random port number to which RFC server of this peer is listening
# Ports must be in the range [65400-65500] since NC State University VCL/EOS
# blocks all other ports
RFC_PORT = randint(65400, 65500)


# The program execution starts here. It prompts the user to specify his/her
# file space where all RFCs file will be kept and downloaded to.
file_space = raw_input('> Please specify YOUR own file space (directory): ')
while not os.path.isdir(file_space):
    if file_space.upper() == 'EXIT':
        exit()
    print file_space + ': No such file or directory'
    file_space = raw_input('> Please specify YOUR own file space (relative '
                           'directory: ')

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
rfc_host_server = gethostbyname(gethostname())
rfc_port_server = rfc_socket.getsockname()[1]

try:
    assert rfc_host_server != '127.0.1.1'
except AssertionError:
    print 'Warning: Program unable to determine IP address of the host you ' \
          'are running on...'
    rfc_host_server = raw_input('> Please specify the IP address of your '
                                'host: ')
    print 'Imported: {}'.format(rfc_host_server)

# RFC server port must be what was defined previously as random
try:
    assert rfc_port_server == RFC_PORT, \
        'Exception: RFC server port does not match. Exiting now...'
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
            request_data = connection_socket.recv(MAX_BUFFER_SIZE)
            while len(request_data) == MAX_BUFFER_SIZE:
                request_data += connection_socket.recv(MAX_BUFFER_SIZE)
            print '\n', request_data.decode()
            try:
                assert PROTOCOL_EOP in request_data.decode(), \
                    'Exception: Undefined App Layer Protocol...'
                if request_data.decode().split()[1] == 'RFC':
                    rfc_file_name = RFC_FILE.format(
                        file_space, request_data.decode().split()[2])
                    response_message = extract_rfc_server_data_protocol(
                        request_data.decode(), os.stat(rfc_file_name).st_size)
                else:
                    rfc_file_name = None
                    response_message = extract_rfc_server_data_protocol(
                        request_data.decode())
                connection_socket.send(response_message.encode())
                if request_data.decode().split()[1] == 'RFC' and (
                            'OK' and '200') in response_message:
                    peer_response = connection_socket.recv(MAX_BUFFER_SIZE)
                    assert 'Accepting' in peer_response.decode(), \
                        'Exception: Synchronization of messages...'
                    rfc_file = open(rfc_file_name, 'rb')
                    sending_data = rfc_file.read(MAX_BUFFER_SIZE)
                    while sending_data:
                        connection_socket.send(sending_data)
                        sending_data = rfc_file.read(MAX_BUFFER_SIZE)
                    rfc_file.close()
                    connection_socket.shutdown(SHUT_RDWR)
            except AssertionError, _e:
                print _e
            connection_socket.close()
            del connection_socket


class RfcIndex:
    def __init__(self, index, title, file_size, hostname=rfc_host_server,
                 port=RFC_PORT):
        self.index = index
        self.title = title
        self.file_size = file_size
        self.hostname = hostname
        self.port = port
        self.ttl = TTL
        self.reg_time = time.time()


def extract_rfc_server_data_protocol(request_data, file_size=None):
    request_list = request_data.split()
    item = request_list[1]
    if item == 'RFC-INDEX':
        version = request_list[2]
    elif item == 'RFC':
        version = request_list[3]
    else:
        version = None
    try:
        assert version == PROTOCOL, 'Exception: Undefined App Layer Protocol...'
    except AssertionError, _e:
        print _e
        header = PEER_RESPONSE_HEADER.format(417, 'Expectation Failed')
        return header + PROTOCOL_EOP
    if item == 'RFC-INDEX':
        if local_rfcs:
            header = PEER_RESPONSE_HEADER.format(200, 'OK')
            protocol = header
            for i, rfc in local_rfcs.iteritems():
                protocol += PROTOCOL_RFC_INDEX.format(
                    rfc.index,  rfc.title, rfc.file_size, rfc.hostname)
        else:
            header = PEER_RESPONSE_HEADER.format(
                404, 'Not Found [No RFC Indexes on peer \'{}\' are '
                     'found]'.format(rfc_host_server))
            protocol = header
    elif item == 'RFC':
        index = int(request_list[2])
        if index in local_rfcs:
            header = PEER_RESPONSE_HEADER.format(200, 'OK')
            protocol = header + 'Size: {}\n'.format(file_size)
        else:
            header = PEER_RESPONSE_HEADER.format(
                404, 'Not Found [No Such RFC Index \'{}\' on peer \'{}\' '
                     'found]'.format(index, rfc_host_server))
            protocol = header
    else:
        protocol = PEER_RESPONSE_HEADER.format(417, 'Expectation Failed')
    protocol += PROTOCOL_EOP
    return protocol


def update():
    rfcs = os.listdir(file_space)
    if rfcs:
        for rfc in rfcs:
            index = int(re.search(r'\d+', rfc).group())
            if index not in local_rfcs:
                file_size = os.stat(file_space + '/' + rfc).st_size
                with open(file_space + '/' + rfc, 'r') as rfc_file:
                    lines = rfc_file.read().splitlines()
                    title = ''
                    for i in range(len(lines)):
                        if lines[i] == 'Abstract':
                            title_split = 2
                            while lines[i - title_split]:
                                title = lines[i - title_split].lstrip() + ' ' \
                                        + title
                                title_split += 1
                    title = title.strip()
                    rfc_index = RfcIndex(index, title, file_size)
                    local_rfcs[index] = rfc_index


def do_show_rfc_remote():
    if remote_rfcs:
        print 'Remote RFCs found by requesting RFCQuery from active peers:'
        for rfc in remote_rfcs:
            diff_time = time.time() - rfc.reg_time
            rfc.ttl = 0 if TTL - int(diff_time) < 0 else TTL - int(diff_time)
            print 'Index: {} '.format(rfc.index), \
                'Title: \'{}\' '.format(rfc.title), \
                'Size: {} '.format(rfc.file_size), \
                'Hostname: {} '.format(rfc.hostname), \
                'TTL: {}'.format(rfc.ttl)
    else:
        print 'No RFCs are found remotely. Obtain RFC Indexes use ' \
              '\'rfcquery\' command.'


def do_show_rfc_local():
    if local_rfcs:
        print 'Local RFCs stored in the directory: \'{}\''.format(file_space)
        for index, rfc in local_rfcs.iteritems():
            print 'Index: {} '.format(rfc.index), \
                'Title: \'{}\' '.format(rfc.title), \
                'Size: {} '.format(rfc.file_size), \
                'Hostname: {} '.format(rfc.hostname), \
                'TTL: {}'.format(rfc.ttl)
    else:
        print 'No RFCs are found in the directory \'{}\''.format(file_space)


class RegisterServer:
    def __init__(self):
        self.cookie = None
        self.dict_active_peers = None


# Create TCP client socket for Register Server on well-known port and initiate
# connection with the Register Server
def send_rs_request():
    client_socket = socket(AF_INET, SOCK_STREAM)
    try:
        client_socket.connect((SERVER_IP, SERVER_PORT))
        rs_request_message = encapsulate_rs_request_data_protocol()
        client_socket.send(rs_request_message.encode())
        rs_response_message = client_socket.recv(MAX_BUFFER_SIZE)
        while len(rs_response_message) == MAX_BUFFER_SIZE:
            rs_response_message += client_socket.recv(MAX_BUFFER_SIZE)
        print rs_response_message.decode()
        assert PROTOCOL_EOP in rs_response_message, \
            'Exception: Undefined App Layer Protocol...'
        register_server.dict_active_peers = extract_rs_response_data_protocol(
            rs_response_message.decode())
    except AssertionError, _e:
        print _e
    except (error, herror, gaierror, timeout), (_value, _message):
        print 'Exception: Creating TCP socket and connecting to Register ' \
              'Server: \'{}\''.format(SERVER_IP)
        print _message
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
        if register_server.cookie is None:
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
        dict_active_peers = dict(zip(ports, hosts))
        return dict_active_peers
    return None


def encapsulate_rs_request_data_protocol():
    if request == 'PQUERY':
        header = RS_PROTOCOL_HEADER.format('GET', request)
    else:
        header = RS_PROTOCOL_HEADER.format('POST', request)
    host_port = PROTOCOL_HOST_PORT.format(rfc_host_server, rfc_port_server)
    cookie = PROTOCOL_COOKIE.format(register_server.cookie)
    _os_ = PROTOCOL_OS.format(platform.platform())
    date = PROTOCOL_DATE.format(datetime.datetime.now())
    protocol = header + host_port + cookie + _os_ + date + PROTOCOL_EOP
    return protocol


# Create TCP client socket for each active RFC server in the P2P-DI system on
# the given IP address and port. Initiate connection with the each active peer.
def send_peer_rfc_query_request():
    if not register_server.dict_active_peers:
        print 'No active peers found... RFC query is not sent...'
        return
    for port, host in register_server.dict_active_peers.iteritems():
        client_socket = socket(AF_INET, SOCK_STREAM)
        try:
            client_socket.connect((host, int(port)))
            this_port = client_socket.getsockname()[1]
            peer_request_message = encapsulate_peer_request_data_protocol(
                this_port)
            client_socket.send(peer_request_message.encode())
            peer_response_message = client_socket.recv(MAX_BUFFER_SIZE)
            while len(peer_response_message) == MAX_BUFFER_SIZE:
                peer_response_message += client_socket.recv(MAX_BUFFER_SIZE)
            print peer_response_message.decode()
            assert PROTOCOL_EOP in peer_response_message, \
                'Exception: Undefined App Layer Protocol...'
            extract_peer_response_data_protocol(peer_response_message, host,
                                                port)
        except AssertionError, _e:
            print _e
        except (error, herror, gaierror, timeout), (_value, _message):
            print 'Exception: Creating TCP socket and connecting to RFC ' \
                  'Server: \'{}\' Port: \'{}\' '.format(host, port)
            print _message
        client_socket.close()
        del client_socket


def encapsulate_peer_request_data_protocol(port, index=None):
    if index is None:
        header = GET_RFC_QUERY_HEADER
    else:
        header = GET_RFC_HEADER.format(index)
    host_port = PROTOCOL_HOST_PORT.format(rfc_host_server, port)
    _os_ = PROTOCOL_OS.format(platform.platform())
    date = PROTOCOL_DATE.format(datetime.datetime.now())
    protocol = header + host_port + _os_ + date + PROTOCOL_EOP
    return protocol


def extract_peer_response_data_protocol(response, host, port):
    response_list = response.split()
    version = response_list[0]
    try:
        assert version == PROTOCOL, 'Exception: Undefined App Layer Protocol...'
    except AssertionError, _e:
        print _e
        return
    status_code = int(response_list[1])
    if request == 'RFCQUERY' and status_code == 200:
        titles = []
        for i in range(len(response_list)):
            if i < len(response_list):
                if response_list[i] == 'Title:' and response_list[
                            i + 1] == '<start>':
                    title = ''
                    i += 2
                    while response_list[i] != '<end>':
                        title += response_list[i] + ' '
                        del response_list[i]
                    title = title.strip()
                    titles.append(title)
        indexes = [response_list[i + 1] for i in range(len(response_list)) if
                   response_list[i] == 'Index:']
        sizes = [response_list[i + 1] for i in range(len(response_list)) if
                 response_list[i] == 'Size:']
        hosts = [response_list[i + 1] for i in range(len(response_list)) if
                 response_list[i] == 'Host:']
        try:
            assert_err = 'Exception: Number of RFC indexes: \'{}\' does not  ' \
                         'match the corresponding number of either their ' \
                         'titles: \'{}\', or sizes: \'{}\', or hosts: \'{}\' ' \
                         'returned from the peer: \'{}\''.format(
                             len(indexes), len(titles), len(sizes), len(hosts),
                             host)
            assert len(indexes) == len(titles) and len(indexes) == len(sizes) \
                and len(indexes) == len(hosts), assert_err
            for h in hosts:
                assert h == host, 'Exception: Hostname of the peer: \'{}\' ' \
                                  'where request is sent differs from the ' \
                                  'hostname included in the returned ' \
                                  'protocol ...'.format(host, h)
        except AssertionError, _e:
            print _e
            return
        for i in range(len(indexes)):
            rfc_index = RfcIndex(indexes[i], titles[i], sizes[i],
                                 hostname=hosts[i], port=port)
            remote_rfcs.append(rfc_index)


def send_peer_rfc_request():
    if user_index in local_rfcs:
        print 'Requested RFC \'{}\' exists locally in \'{}\' ' \
              'directory...'.format(user_index, file_space)
        return
    for rfc in remote_rfcs:
        if int(rfc.index) == user_index:
            diff_time = time.time() - rfc.reg_time
            if TTL - int(diff_time) < 0:
                rfc.ttl = 0
                print 'RFC server: \'{}\' has expired TTL=0 for ' \
                      'RFC \'{}\'...'.format(rfc.hostname, user_index)
            else:
                client_socket = socket(AF_INET, SOCK_STREAM)
                client_socket.connect((rfc.hostname, int(rfc.port)))
                this_port = client_socket.getsockname()[1]
                peer_request_message = encapsulate_peer_request_data_protocol(
                    this_port, index=user_index)
                client_socket.send(peer_request_message.encode())
                peer_response_message = client_socket.recv(MAX_BUFFER_SIZE)
                while len(peer_response_message) == MAX_BUFFER_SIZE:
                    peer_response_message += client_socket.recv(MAX_BUFFER_SIZE)
                print peer_response_message.decode()
                try:
                    assert PROTOCOL_EOP in peer_response_message, \
                        'Exception: Undefined App Layer Protocol...'
                    assert 'OK' and '200' in peer_response_message.decode(), \
                        'Exception: RFC server: \'{}\' does not have ' \
                        'requested RFC \'{}\'...'.format(rfc.hostname,
                                                         user_index)
                except AssertionError, _e:
                    print _e
                    client_socket.close()
                    del client_socket
                    return
                client_socket.send('Accepting'.encode())
                with open(RFC_FILE.format(file_space, user_index), 'wb') as \
                        rfc_file:
                    receiving = True
                    while receiving:
                        data_file = client_socket.recv(MAX_BUFFER_SIZE)
                        if not data_file:
                            receiving = False
                        else:
                            rfc_file.write(data_file)
                client_socket.close()
                del client_socket
                update()
                return
    print 'Requested RFC \'{}\' not found at any remote peers...'.format(
        user_index)


def do_show_peer():
    if not register_server.dict_active_peers:
        print 'Not Found [No other active peers in the P2P-DI system found]'
        print 'Please update list of active peers with \'pquery\' command'
    else:
        for port, host in register_server.dict_active_peers.iteritems():
            print 'Host: {}, Port: {}'.format(host, port)


# Create and start new main thread that deals with the RFC server.
# All requests from other peers will be coming coming to welcoming port of this
# RFC server.
rfc_server_thread = RfcServer()
rfc_server_thread.start()

# Define key variables
local_rfcs = {}
remote_rfcs = []
register_server = RegisterServer()
update()

"""
This is the main thread that continuously prompts the user for new command. 
It will loop forever until user sends exit command.
"""
while True:
    command = raw_input('> ').upper()
    command_fields = command.split(' ')
    request = command_fields[0]
    if request in RS_REQUESTS:
        send_rs_request()
    elif request == 'RFCQUERY':
        send_peer_rfc_query_request()
    elif request == 'GET':
        if command_fields[1] == 'RFC' and len(command_fields) == 3:
            try:
                user_index = int(command_fields[2])
                send_peer_rfc_request()
            except ValueError:
                print 'Exception: RFC number provided: \'{}\' is not ' \
                      'provided type of Integer...\nusage: get rfc ' \
                      'arg1: [integer value]'.format(command_fields[1])
        else:
            print 'usage: get rfc number'
    elif request == 'SHOW':
        if len(command_fields) == 3:
            if command_fields[1] == 'RFC' and command_fields[2] == 'LOCAL':
                do_show_rfc_local()
            elif command_fields[1] == 'RFC' and command_fields[2] == 'REMOTE':
                do_show_rfc_remote()
            else:
                print 'usage: show arg1: [peer, rfc] rfc arg2: [local, remote]'
        elif len(command_fields) == 2:
            if command_fields[1] == 'RFC':
                do_show_rfc_local()
                print '*-' * 40
                do_show_rfc_remote()
            elif command_fields[1] == 'PEER':
                do_show_peer()
            else:
                print 'usage: show arg1: [peer, rfc] rfc arg2: [local, remote]'
        else:
            print 'usage: show arg1: [peer, rfc] rfc arg2: [local, remote]'
    elif request == 'UPDATE':
            update()
    elif request == 'HELP':
        try:
            with open('help_peers.txt', 'r') as fin:
                print fin.read()
        except Exception as e:
            print e.__doc__, type(e).__name__, e.message
            print 'File \'help_peers.txt\' not found. Please import file in ' \
                  'local directory: \'{}\''.format(file_space)
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
        print 'Command not found. Use \'help\' to see proper commands.\n'
