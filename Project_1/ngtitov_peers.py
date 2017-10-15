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


# The Application Layer Protocol for peer-to-RegisterServer REQUEST
# communication of P2P-DI/1.0 protocol is defined:
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
| Date:   |  Year-Month-Day Hour-Min-Sec-mSec   |
-------------------------------------------------
|            EOP (End of Protocol)              |
-------------------------------------------------
"""

# The Application Layer Protocol for RegisterServer-to-peer RESPONSE
# communication of P2P-DI/1.0 protocol is defined:
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

# The Application Layer Protocol for peer-to-RFCServer (another peer) REQUEST
# communication of P2P-DI/1.0 protocol is defined:
"""
-----------------------------------------------------------------
| Type  | Method | Index (optional) | Protocol name and version |
-----------------------------------------------------------------
| Host: |  IPv4  |       Port:      |          Integer          |
-----------------------------------------------------------------
|  OS:  |                       System                          |
-----------------------------------------------------------------
| Date: |         Year-Month-Day Hour-Min-Sec-mSec              |
-----------------------------------------------------------------
|                  EOP (End of Protocol)                        |
-----------------------------------------------------------------
"""

# The Application Layer Protocol for RFCServer-to-peer RESPONSE
# communication for RFCQuery request of P2P-DI/1.0 protocol is defined:
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

# The Application Layer Protocol for RFCServer-to-peer RESPONSE
# communication for Get RFC request of P2P-DI/1.0 protocol is defined.
# Note that header protocol comes as plane text, but the requested RFC
# document itself in the binary mode:
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
                RFC Server closes socket
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


# The program execution starts here.It prompts the user to specify his/her
# file space where all RFCs file will be kept and downloaded to.
file_space = raw_input('> Please specify YOUR own file space (directory): ')
while not os.path.isdir(file_space):
    if file_space.upper() == 'EXIT':
        exit()
    print file_space + ': No such file or directory'
    file_space = raw_input('> Please specify YOUR own file space (relative '
                           'directory: ')

# Determine IP address of this RFC server
rfc_host_server = gethostbyname(gethostname())

# Some systems may have IP 127.0.1.1 addresses in /etc/hosts file that effects
# finding of real IP address
try:
    assert rfc_host_server != '127.0.1.1'
except AssertionError:
    print 'Warning: Program unable to determine IP address of the host you ' \
          'are running on...'
    rfc_host_server = raw_input('> Please specify the IP address of your '
                                'host: ')
    print 'Imported: {}'.format(rfc_host_server)


class RfcServer(threading.Thread):
    """Implements RFC Server as the main thread.

    It handles multiple simultaneous connections for downloads (of the RFC
    index or an RFC document) by remote peers. The main thread opens RFC
    Server TCP welcoming port to which RFC server of this peer is listening,
    creates new socket and binds it to that port. Port number is generated
    randomly in the range [65400-65500] since NC State University VCL/EOS
    blocks all other ports. Then it starts listening to the that
    peer-specific port. When a connection from a remote peer is established,
    the main thread spawns a new thread that handles the downloading for
    this remote peer. The main thread then returns to listening for other
    connection requests.

    Attributes:
        running: A boolean indicating whether main thread needs to terminate.
        port: the port number to which the RFC Server of this peer listens.
    """
    def __init__(self):
        """Initiates RfcServer class with main thread."""
        threading.Thread.__init__(self)
        self.running = True
        self.port = None

    def run(self):
        """Runs the main thread of the RFC Server."""
        # Create new TCP server welcoming port and socket. Bind that socket to
        # that new port.
        self.port = randint(65400, 65500)
        rfc_server_socket = socket(AF_INET, SOCK_STREAM)
        try:
            rfc_server_socket.bind(('', self.port))
            # RFC Server begins listening for incoming TCP requests from other
            # peers by queueing up as many as 5 connect requests
            rfc_server_socket.listen(5)
            print 'RFC server is initialized and listing ...'
        except error, (value, message):
            print 'Exception while creating and binding RFC welcoming socket:'
            print message
            rfc_server_socket.close()
            del rfc_server_socket
            return
        # Loop forever waiting for new connections from different peers
        while self.running:
            try:
                # Wait on accept and create new socket
                connection_socket, address = rfc_server_socket.accept()
                if self.running:
                    # Spawn a new thread that handles this request and go
                    # back to wait on accept
                    new_rfc_server_thread = RfcRequestHandler(connection_socket,
                                                              address)
                    new_rfc_server_thread.start()
                    rfc_server_threads_list.append(new_rfc_server_thread)
            finally:
                if not self.running:
                    print 'Shut down the RFC server welcoming port ...'
                    connection_socket.close()
                    del connection_socket

    def stop(self):
        """Stops the main thread of the RFC Server.

        Creates a socket and initiates the connection with itself to trigger
        accept function.
        """
        self.running = False
        self_socket = socket(AF_INET, SOCK_STREAM)
        try:
            self_socket.connect((rfc_host_server, self.port))
        except error, (value, message):
            print message
        self_socket.close()
        del self_socket


class RfcRequestHandler(threading.Thread):
    """Handles request of other peer as a newly created thread.

    This is a new thread that was created by the main RFC Server thread. It
    reads the request by extracting data from P2P-DI/1.0 protocol, executes
    request, builds response message by encapsulating return data based on
    P2P-DI/1.0 protocol and sends it back to the peer which made request.

    Attributes:
        connection_socket: socket object for send and receive data.
        address: address bound to the socket.
    """
    def __init__(self, connection_socket, address):
        """Initiates the HandleRfcRequest class with new thread and socket
        attributes.
        """
        threading.Thread.__init__(self)
        self.connection_socket = connection_socket
        self.address = address

    def run(self):
        """Runs the new thread to execute request and send response back."""
        # Read peer's request data from socket
        request_data = self.connection_socket.recv(MAX_BUFFER_SIZE)
        while len(request_data) == MAX_BUFFER_SIZE:
            request_data += self.connection_socket.recv(MAX_BUFFER_SIZE)
        print '\n', request_data.decode()
        try:
            assert PROTOCOL_EOP in request_data.decode(), \
                'Exception: Undefined App Layer Protocol...'
            if request_data.decode().split()[1] == 'RFC-INDEX':
                # This is GET-INDEX RFC request
                print 'Nikolay: this is GET RFC document 1'
                response_message = extract_rfc_server_data_protocol(
                    request_data.decode())
                # Send the response data back
                self.connection_socket.send(response_message.encode())
            elif request_data.decode().split()[1] == 'RFC':
                # This is GET RFC document request
                rfc_file_name = RFC_FILE.format(
                    file_space, request_data.decode().split()[2])
                response_message = extract_rfc_server_data_protocol(
                    request_data.decode(), os.stat(rfc_file_name).st_size)
                # Send the response data back
                self.connection_socket.send(response_message.encode())
                # Once response is sent back and if this was successful GET RFC
                # request, send RFC file back
                if ('OK' and '200') in response_message:
                    print 'Nikolay: This is Get RFC document 2'
                    # Ensure peer is ready to accept binary data
                    peer_response = self.connection_socket.recv(MAX_BUFFER_SIZE)
                    assert 'Accepting' in peer_response.decode(), \
                        'Exception: Synchronization of messages ...'
                    rfc_file = open(rfc_file_name, 'rb')
                    sending_data = rfc_file.read(MAX_BUFFER_SIZE)
                    while sending_data:
                        self.connection_socket.send(sending_data)
                        sending_data = rfc_file.read(MAX_BUFFER_SIZE)
                    rfc_file.close()
                    self.connection_socket.shutdown(SHUT_RDWR)
        except AssertionError, _e:
            print _e
        # Close the socket and delete it since this thread is done
        self.connection_socket.close()
        del self.connection_socket


class RfcIndex:
    """RFC Index class for RFC document record that contains information about
    local and remote RFC documents.

    Attributes:
        index: the RFC number.
        title: the title of the RFC.
        file_size: the size of the RFC document.
        hostname: the hostname of the peer containing the RFC.
        port: the port number of the peer containing the RFC.
    """
    def __init__(self, index, title, file_size, port, hostname=rfc_host_server):
        """Initiates RfcIndex class with all attributes."""
        self.index = index
        self.title = title
        self.file_size = file_size
        self.port = port
        self.hostname = hostname
        self.ttl = TTL
        self.reg_time = time.time()


def extract_rfc_server_data_protocol(request_data, file_size=None):
    """Extracts request from the protocol that is sent to this RFC server.

    It reads the request by extracting data from P2P-DI/1.0 protocol,
    executes request, builds response message by encapsulating return data
    based on P2P-DI/1.0 protocol and returns it.

    Args:
        request_data: the entire P2P-DI/1.0 protocol as a string.
        file_size: Size of the RFC document if needs to be transferred.

    Returns:
        Protocol that contains response message addressed to the peer.
    """
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
            # Insert all the local RFC indexes into the protocol.
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
    """Updates the list of RFC indexes if new RFC documents were added
    manually into file space of the user.

    Opens the file space of the user and reads each file. If the file is not
    in the list - adds it.
    """
    rfcs = os.listdir(file_space)
    if rfcs:
        for rfc in rfcs:
            index = int(re.search(r'\d+', rfc).group())
            if index not in local_rfcs:
                file_size = os.stat(file_space + '/' + rfc).st_size
                with open(file_space + '/' + rfc, 'r') as rfc_file:
                    lines = rfc_file.read().splitlines()
                    # Get the title. It is above Abstraction section.
                    title = ''
                    for i in range(len(lines)):
                        if lines[i] == 'Abstract':
                            title_split = 2
                            while lines[i - title_split]:
                                title = lines[i - title_split].lstrip() + ' ' \
                                        + title
                                title_split += 1
                    title = title.strip()
                    rfc_index = RfcIndex(index, title, file_size,
                                         rfc_server_main_thread_list[0].port)
                    local_rfcs[index] = rfc_index


def do_show_rfc_remote():
    """Displays/prints to the console all RFC indexes that were obtained from
    remote RFC
    servers.
    """
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
    """Displays/prints to the console all local RFC indexes that are kept in
    the file space of the user.
    """
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


def do_show_peer():
    """Displays/prints all active peers in the P2P-DI system."""
    if not register_server.list_active_peers:
        print 'Not Found [No other active peers in the P2P-DI system found]'
        print 'Please update list of active peers with \'pquery\' command'
    else:
        for dict_active_peer in register_server.list_active_peers:
            host, port = dict_active_peer.items()[0]
            print 'Host: {}, Port: {}'.format(host, port)


class RegisterServer:
    """Facilitates communication with Register Server.

    Attributes:
        cookie: assigned to this peer by RS.
        list_active_peers: list of dictionaries of active peers.
    """
    def __init__(self):
        """Initiates RegisterServer with attributes."""
        self.cookie = None
        self.list_active_peers = None


def send_rs_request():
    """Sends request obtained from the user (prompt) to the Register Server.

    Creates TCP client socket for Register Server on well-known port and
    initiates connection with the Register Server. Creates the request
    message by encapsulating data into P2P-DI/1.0 protocol, waits for the
    response from Register Server, and calls helper function to extract
    response data from P2P-DI/1.0 protocol. Support only four request
    methods that may come from the user - Register, Leave, PQuery,
    and KeepAlive.
    """

    if not rfc_server_main_thread_list[0].running and request == RS_REQUESTS[0]:
        # The main RFC Server thread has stopped. Spinning it up again.
        del rfc_server_main_thread_list[0]
        new_main_rfc_server_thread = RfcServer()
        new_main_rfc_server_thread.start()
        rfc_server_main_thread_list.append(new_main_rfc_server_thread)
    client_socket = socket(AF_INET, SOCK_STREAM)
    try:
        client_socket.connect((SERVER_IP, SERVER_PORT))
        rs_request_message = encapsulate_rs_request_data_protocol()
        client_socket.send(rs_request_message.encode())
        rs_response_message = client_socket.recv(MAX_BUFFER_SIZE)
        while len(rs_response_message) == MAX_BUFFER_SIZE:
            rs_response_message += client_socket.recv(MAX_BUFFER_SIZE)
        print rs_response_message.decode()
        assert PROTOCOL_EOP and PROTOCOL in rs_response_message, \
            'Exception: Undefined App Layer Protocol...'
        # Call helper function to extract response data
        extract_rs_response_data_protocol(rs_response_message.decode())
    except AssertionError, _e:
        print _e
    except (error, herror, gaierror, timeout), (_value, _message):
        print 'Exception: Creating TCP socket and connecting to Register ' \
              'Server: \'{}\''.format(SERVER_IP)
        print _message
    client_socket.close()
    del client_socket


def extract_rs_response_data_protocol(response):
    """Extracts response data from the protocol that is received from RS.

    It reads the response by extracting data from P2P-DI/1.0 protocol and
    performs required steps according to the request message. If it was
    Register request save the cookie, if it was leave request - stop RFC
    Server and if it was PQuery request save all active peers.

    Args:
        response: the entire P2P-DI/1.0 protocol as a string.
    """
    response_list = response.split()
    version = response_list[0]
    status_code = int(response_list[1])
    phrase = response_list[2]
    try:
        assert version == PROTOCOL, 'Exception: Undefined App Layer Protocol...'
        if request == RS_REQUESTS[0]:
            # This is Register request, save cookie if it was assigned.
            assert status_code in [200, 201] and phrase in ['OK', 'Created'], \
                'Exception: Register Server did not register peer ...'
            # Save the cookie if it was not yet assigned to this peer.
            if register_server.cookie is None:
                register_server.cookie = response_list[response_list.index(
                    'Cookie:') + 1]
        elif request == RS_REQUESTS[1]:
            # This is Leave request, stop RFC server if it runs.
            if status_code == 200 and phrase == 'OK' and \
                    rfc_server_main_thread_list[0].running:
                print 'Stopping RFC Server...'
                rfc_server_main_thread_list[0].stop()
                rfc_server_main_thread_list[0].join()
                print 'Wait for all the RFC server threads to terminate ...'
                for _t_ in rfc_server_threads_list:
                    _t_.join()
        elif request == RS_REQUESTS[2] and status_code == 302:
            # This is PQuery request, save all active peers.
            hosts = [response_list[i + 1] for i in range(len(response_list)) if
                     response_list[i] == 'Host:']
            ports = [response_list[i + 1] for i in range(len(response_list)) if
                     response_list[i] == 'Port:']
            assert len(hosts) == len(ports), \
                'Number of active hosts IP addresses: \'{}\' does not match ' \
                'the corresponding number of their ports: \'{}\' return from ' \
                'the Register Server \'{}\''.format(len(hosts), len(ports),
                                                    SERVER_IP)
            list_active_peers = []
            for i in range(len(hosts)):
                dict_active_peer = dict([(hosts[i], ports[i])])
                list_active_peers.append(dict_active_peer)
            register_server.list_active_peers = list_active_peers
    except AssertionError, _e:
        print _e


def encapsulate_rs_request_data_protocol():
    """Encapsulates request data addressed to Register Server from the user
    into P2P-DI/1.0 protocol.

    Builds the Register Server request by encapsulating the data obtained
    from the user and includes additional parameters into P2P-DI/1.0 protocol.

    Returns:
        Protocol that contains request message to the Register Server.
    """
    if request == 'PQUERY':
        header = RS_PROTOCOL_HEADER.format('GET', request)
    else:
        header = RS_PROTOCOL_HEADER.format('POST', request)
    host_port = PROTOCOL_HOST_PORT.format(rfc_host_server,
                                          rfc_server_main_thread_list[0].port)
    cookie = PROTOCOL_COOKIE.format(register_server.cookie)
    _os_ = PROTOCOL_OS.format(platform.platform())
    date = PROTOCOL_DATE.format(datetime.datetime.now())
    protocol = header + host_port + cookie + _os_ + date + PROTOCOL_EOP
    return protocol


def send_peer_rfc_request():
    """Requests RFC document from the RFC server of active peer.

    The RFC document transfer happens similar to four-way handshake.
    Initially, the RFC document is specified by the user input. It creates
    TCP client socket for RFC Server to one of the active peers on the port
    that was obtained from Register Server and initiate connection with that
    RFC server. Then it creates the RFC document request and encapsulates
    data into P2P-DI/1.0 protocol. Sends request and waits for the response
    from RFC server, ensures that RFC server contains requested RFC document
    by extracting status code and phrase form protocol and then sends its
    accepting key back to the RFC server. Once RFC server received
    acceptance key, it sends RFC document in binary mode back to this
    client. And clients writes the file in the file space of the user.
    """
    if user_index in local_rfcs:
        print 'Requested RFC \'{}\' exists locally in \'{}\' ' \
              'directory...'.format(user_index, file_space)
        return
    for rfc in remote_rfcs:
        # Find requested RFC document
        if int(rfc.index) == user_index:
            diff_time = time.time() - rfc.reg_time
            if TTL - int(diff_time) < 0:
                rfc.ttl = 0
                print 'RFC server: \'{}\' has expired TTL=0 for ' \
                      'RFC \'{}\'...'.format(rfc.hostname, user_index)
            else:
                client_socket = socket(AF_INET, SOCK_STREAM)
                try:
                    client_socket.connect((rfc.hostname, int(rfc.port)))
                    this_port = client_socket.getsockname()[1]
                    # Build request message protocol
                    peer_request_message = \
                        encapsulate_peer_request_data_protocol(this_port,
                                                               index=user_index)
                    client_socket.send(peer_request_message.encode())
                    peer_response_message = client_socket.recv(MAX_BUFFER_SIZE)
                    while len(peer_response_message) == MAX_BUFFER_SIZE:
                        peer_response_message += client_socket.recv(
                            MAX_BUFFER_SIZE)
                    print peer_response_message.decode()
                    # Ensure RFC server has requested RFC document.
                    assert PROTOCOL_EOP in peer_response_message, \
                        'Exception: Undefined App Layer Protocol...'
                    assert 'OK' and '200' in peer_response_message.decode(), \
                        'Exception: RFC server: \'{}\' does not have ' \
                        'requested RFC \'{}\'...'.format(rfc.hostname,
                                                         user_index)
                    # Ready to start accepting RFC document in binary mode.
                    client_socket.send('Accepting'.encode())
                    # Write into the file.
                    with open(RFC_FILE.format(file_space, user_index),
                              'wb') as rfc_file:
                        receiving = True
                        while receiving:
                            data_file = client_socket.recv(MAX_BUFFER_SIZE)
                            if not data_file:
                                receiving = False
                            else:
                                rfc_file.write(data_file)
                    # Done
                    client_socket.close()
                    del client_socket
                    update()
                    return
                except (error, herror, gaierror, timeout), (_value, _message):
                    print 'Exception: Creating TCP socket and connecting to ' \
                          'RFC  Server: \'{}\' Port: \'{}\' '.format(
                              rfc.hostname, rfc.port)
                    print _message
                except AssertionError, _e:
                    print _e
                client_socket.close()
                del client_socket
    print 'Requested RFC \'{}\' not found at any remote peers...'.format(
        user_index)


def send_peer_rfc_query_request():
    """Requests RFC-Index from the RFC server of active peer.

    The RFC-Index request is made by the user. It creates TCP client socket
    for RFC Server to one of the active peers on the port that was obtained
    from Register Server and initiates connection with that RFC server. Then
    it creates the RFC-Index request and encapsulates data into P2P-DI/1.0
    protocol. Sends request and waits for the response from RFC server. Once
    response is obtained it call for extraction of the data protocol.
    """
    if not register_server.list_active_peers:
        print 'No active peers found... RFC query is not sent...'
        return
    for dict_active_peer in register_server.list_active_peers:
        host, port = dict_active_peer.items()[0]
        client_socket = socket(AF_INET, SOCK_STREAM)
        try:
            client_socket.connect((host, int(port)))
            this_port = client_socket.getsockname()[1]
            # Create RFC-Index request message.
            peer_request_message = encapsulate_peer_request_data_protocol(
                this_port)
            # Send request to the RFC server.
            client_socket.send(peer_request_message.encode())
            peer_response_message = client_socket.recv(MAX_BUFFER_SIZE)
            print 'Size of response message: ', len(peer_response_message)
            while len(peer_response_message) == MAX_BUFFER_SIZE:
                print 'Nikolay'
                peer_response_message += client_socket.recv(MAX_BUFFER_SIZE)
            print peer_response_message.decode()
            assert PROTOCOL_EOP in peer_response_message, \
                'Exception: Undefined App Layer Protocol...'
            # Extract the data from RFC Server response message.
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
    """Encapsulates request data addressed to RFC Server from the user into
    P2P-DI/1.0 protocol.

    Builds the RFC server request by encapsulating the data obtained from
    the user and includes additional parameters into P2P-DI/1.0 protocol.

    Returns:
        Protocol that contains request message addressed to the RFC Server.
    """
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
    """Extracts RFC-Indexes and adds them to the list maintained by the
    main thread.

    It reads the response message from one of the RFC Servers and extracts
    RFC-Indexes data from P2P-DI/1.0 protocol, creates new object for each
    RFC-Index it obtain by invoking RfcIndex class and adds obtained data
    into remote_frc list.

    Args:
        response: the entire P2P-DI/1.0 protocol as a string.
        host: hostname of the RFC server.
        port: port of the RFC server.

    Returns: Modifies the list of remote RFCs. Does not return anything.
    """
    response_list = response.split()
    version = response_list[0]
    try:
        assert version == PROTOCOL, 'Exception: Undefined App Layer Protocol...'
    except AssertionError, _e:
        print _e
        return
    status_code = int(response_list[1])
    # Ensure that RFC query request was successful.
    if request == 'RFCQUERY' and status_code == 200:
        # First extract the titles.
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
        # Extract indexes, sizes, and hosts.
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
            # Perform test if received data is consistent.
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
        # Clean remote RFC list and add new RFCs indexes into the list.
        del remote_rfcs[:]
        for i in range(len(indexes)):
            rfc_index = RfcIndex(indexes[i], titles[i], sizes[i], port,
                                 hosts[i])
            remote_rfcs.append(rfc_index)


# Actual program starts here.
# Create and start new main thread that deals with the RFC server.
# All requests from other peers will be coming coming to welcoming port of this
# RFC server.
main_rfc_server_thread = RfcServer()
main_rfc_server_thread.start()
time.sleep(0.1)

# Define key variables
local_rfcs = {}
remote_rfcs = []
rfc_server_main_thread_list = [main_rfc_server_thread]
rfc_server_threads_list = []
register_server = RegisterServer()
# Update the list of RFC Indexes.
update()


# This is the main thread that continuously prompts the user for new command.
# It will loop forever until user sends exit command.
while True:
    command = raw_input('> ').upper()
    command_fields = command.split(' ')
    request = command_fields[0]
    if request in RS_REQUESTS:
        # This is request to Register Server
        send_rs_request()
    elif request == 'RFCQUERY':
        send_peer_rfc_query_request()
    elif request == 'GET':
        if command_fields[1] == 'RFC' and len(command_fields) == 3:
            try:
                pass
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
                # Separate local and remote RFC indexes by this line.
                print '*-' * 40
                do_show_rfc_remote()
            elif command_fields[1] == 'PEER':
                do_show_peer()
            else:
                print 'usage: show arg1: [peer, rfc] rfc arg2: [local, remote]'
        else:
            print 'usage: show arg1: [peer, rfc] rfc arg2: [local, remote]'
    elif request == 'UPDATE':
        # Update the list of RFC Indexes.
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
        for main_rfc_server_t in rfc_server_main_thread_list:
            if main_rfc_server_t.running:
                print 'Stopping RFC Server...'
                main_rfc_server_t.stop()
                main_rfc_server_t.join()
        print 'Wait for all the RFC server threads to terminate ...'
        for t in rfc_server_threads_list:
            t.join()
        exit('Goodbye')
    elif request == '':
            pass
    else:
        print 'Command not found. Use \'help\' to see proper commands.\n'
