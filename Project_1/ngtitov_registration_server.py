"""
ngtitov_registration_server.py

CSC 573 (601) - Internet Protocols
This program implements the solution the Project 1 assignment: Peer-to-Peer
with Distributed Index (P2P-DI) System for Downloading RFCs.

This is Register Server implementation that only responds to peers in the
P2P-DI system requests based on P2P-DI/1.0 protocol defined below. It
continuously waits for connections from the peers on the well-known port
654231. The RS maintains a peer list data structure with information about
the peers that have registered with the RS at least once. The Registration
Server does not keep any information about the RFCs that various active
peers may have.

This Registration Server is user-driven and may take commands from
interactive user. It also supports limited requests from other peers
strictly defined by the P2P-DI/1.0 protocol. It supports following messages:
- Register: registration message from peer with information about the port
to which its RFC server listens.
- Leave: peer decides to leave P2P-DI system
- PQuery: peer message to obtain a list of active peers that includes the
hostname and RFC server port information.
- KeepAlive: a peer periodically sends this message to the RS to let it know
that it continues to be active.

The Application Layer Protocol of the P2P-DI system is designed for Register
Server  to communicate with other peers. Protocol details are provided below.

@version: 1.0
@todo: None
@since: October 02, 2017

@status: Complete
@requires: help_registration_server.txt file

@contact: ngtitov@ncsu.edu
@author: Nikolay G. Titov
"""


# Import required Python libraries
import datetime
import time
import threading
from socket import *

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


# Initialization of constants
SERVER_PORT = 65423
TTL = 7200
THIRTY_DAYS = 2592000
PROTOCOL = 'P2P-DI/1.0'
STATUS_CODE_PHRASE = ' {} {}\n'
PROTOCOL_COOKIE = 'Cookie: {}\n'
PROTOCOL_ACTIVE_PEERS = 'Host: {} Port: {}\n'
PROTOCOL_EOP = 'EOP'
MAX_BUFFER_SIZE = 1024


class Peer:
    """Maintains peer's data structure with information about the peer.

    This class creates new peer object, maintains its information during the
    registration period and throughout session while both Registration
    Server and peer are running.

    Attributes:
        hostname: string identifying hostname of the peer.
        port: the port number to which the RFC server of this peer listens.
        cookie: integer a unique identifier of the peer.
        flag: boolean indicates whether the peer is currently active.
        reg_date: the most recent date/time that the peer registered.
        ttl: time to live field decremented periodically so that whenever it
             reaches 0 the peer is flagged as inactive. Initialized to 7200
             and updates every time peer contacts the Register Server.
        reg_times: list of all registration dates of the peer.
    """
    def __init__(self, hostname, port, cookie, flag=False):
        """Initiates Peer class with all the attributes."""
        self.hostname = hostname
        self.port = port
        self.cookie = cookie
        self.flag = flag
        self.reg_date = datetime.datetime.now()
        self.ttl = TTL
        self.reg_times = [time.time()]

    def register_update(self, port):
        """Updates registration information of the peer with new values.

        Args:
            port: the port number to which the RFC server of this peer listens.
        """
        self.reg_times.append(time.time())
        self.reg_date = datetime.datetime.now()
        self.port = port
        self.update()

    def leave_update(self):
        """Updates information of the peer per leave request."""
        self.port = None
        self.flag = False
        self.ttl = 0

    def update(self):
        """Updates general information of the peer including flag, reg_times."""
        self.flag = True
        self.reg_times[-1] = time.time()
        _reg_time = time.time()
        for reg_time in self.reg_times:
            if _reg_time - reg_time > THIRTY_DAYS:
                self.reg_times.remove(reg_time)
            else:
                return

    def is_active(self):
        """Performs the test whether the peer is still active and updates
        its TTL field.
        """
        if self.flag:
            diff_time = time.time() - self.reg_times[-1]
            self.ttl = TTL - diff_time
            self.flag = True if self.ttl > 0 else False
            if not self.flag:
                self.ttl = 0


class PeerRequests(threading.Thread):
    """Implements and handles peer request as different thread.

    This class continuously waits for connections from the peers on the
    well-known port 654231. Once the request is obtained from the peer it
    calls helper functions to extract the request information from the
    P2P-DI/1.0 protocol and construct the response message by encapsulating
    response data into protocol. It then sends requested information back to
    the peer.
    """
    def __init__(self):
        """Initiates the HandleRfcRequest class with new thread."""
        threading.Thread.__init__(self)

    def run(self):
        """Runs the new thread to execute request and send response back.

        Continuously waits for connections from the peers on the well-known
        port 654231. Once the request is obtained from the peer it calls
        helper functions to extract the request information and construct
        the response message. Sends response message back to peer.
        """
        # Loop forever waiting for new connections from different peers
        while True:
            # Wait on accept and create new socket
            try:
                connection_socket, address = server_socket.accept()
            except error:
                print 'Shuts down the TCP Register Server welcoming socket...'
                exit()
            # Read peer's request data from socket
            request_data = connection_socket.recv(MAX_BUFFER_SIZE)
            while len(request_data) == MAX_BUFFER_SIZE:
                request_data += connection_socket.recv(MAX_BUFFER_SIZE)
            print '\n', request_data.decode()
            try:
                assert PROTOCOL_EOP in request_data.decode(), \
                    'Exception: Undefined App Layer Protocol..'
                # Obtain response message by extracting request protocol
                response_message = extract_data_protocol(request_data.decode())
                connection_socket.send(response_message.encode())
            except AssertionError, _e:
                print _e
            connection_socket.close()
            del connection_socket


def extract_data_protocol(request_data):
    """Extracts request from the protocol that is received from the peer.

    Extracts request message from P2P-DI/1.0 protocol and calls helper
    function to prepare response message back to the peer.

    Args:
        request_data: the entire P2P-DI/1.0 protocol as a string.

    Returns:
        Protocol that contains response message addressed to the peer.
    """
    data_list = request_data.split()
    method = data_list[1]
    version = data_list[2]
    try:
        assert version == PROTOCOL, 'Exception: Undefined App Layer Protocol...'
    except AssertionError, _e:
        print _e
        response_message = encapsulate_data_protocol(417,
                                                     'Expectation Failed')
        return response_message
    host = data_list[data_list.index('Host:') + 1]
    port = data_list[data_list.index('Port:') + 1]
    cookie = None if data_list[data_list.index('Cookie:') + 1] == 'None' \
        else int(data_list[data_list.index('Cookie:') + 1])
    # Call helper function to prepare response message.
    response_message = execute_request(method, host, port, cookie)
    return response_message


def execute_request(method, host, port, cookie):
    """Executes peer request and prepares response message back to the peer.

    Supports request methods Register, Leave, PQuery, and KeepAlive. Takes
    actions according to the request method. After request is completed it
    calls another helper function that generates the response message by
    encapsulating response data into P2P-DI/1.0 protocol.

    Args:
        method: request method is one of the four supported types.
        host: string identifying hostname of the peer.
        port: the port number to which the RFC Server of the peer listens.
        cookie: integer a unique identifier of the peer.
    Returns:
        Protocol that contains response message addressed to the peer.
    """
    try:
        if method == 'REGISTER':
            if cookie is None:
                # The peer has never register before.
                assert len(dict_peers) not in dict_peers, \
                    'Error: Cookie for the new peer is in use.'
                # Add the peer to the list and assign cookie to it.
                peer = Peer(host, port, cookie=len(dict_peers), flag=True)
                dict_peers[len(dict_peers)] = peer
                # Call helper function to prepare response message.
                response_message = encapsulate_data_protocol(
                    201, 'Created', cookie=peer.cookie)
            else:
                # Peer has registered previously.
                peer = dict_peers.get(cookie)
                peer.register_update(port)
                # Call helper function to prepare response message.
                response_message = encapsulate_data_protocol(200, 'OK',
                                                             cookie=peer.cookie)
        elif method == 'LEAVE':
            peer = dict_peers.get(cookie)
            # Update peer's information per leave request.
            peer.leave_update()
            # Call helper function to prepare response message.
            response_message = encapsulate_data_protocol(200, 'OK')
            return response_message
        elif method == 'PQUERY':
            if cookie is None:
                # Not legal since peer is not registered.
                response_message = encapsulate_data_protocol(
                    403, 'Forbidden [Peer is NOT register with the RS]')
            else:
                peer = dict_peers.get(cookie)
                peer.is_active()
                if not peer.flag:
                    # TTL of the peer is expired.
                    response_message = encapsulate_data_protocol(
                        403, 'Forbidden [Peer is NOT register with the RS]')
                else:
                    # Get all active peer information ready to send to peer.
                    list_active_peers = []
                    for key, active_peer in dict_peers.iteritems():
                        if active_peer.flag and cookie != active_peer.cookie:
                            dict_active_peer = dict([(active_peer.hostname,
                                                      active_peer.port)])
                            list_active_peers.append(dict_active_peer)
                    if list_active_peers:
                        # Call helper function to prepare response message.
                        response_message = encapsulate_data_protocol(
                            302, 'Found', list_active_peers=list_active_peers)
                    else:
                        # No active peers found.
                        response_message = encapsulate_data_protocol(
                            404, 'Not Found [No other active peers in the '
                                 'P2P-DI system found]')
        elif method == 'KEEPALIVE':
            peer = dict_peers.get(cookie)
            peer.update()
            # Call helper function to prepare response message.
            response_message = encapsulate_data_protocol(200, 'OK',
                                                         cookie=peer.cookie)
        else:
            # Not supported request method.
            # Call helper function to prepare response message.
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
                              list_active_peers=None):
    """Encapsulates response data addressed to the peer into protocol.

    Prepares the response message back for the peer by encapsulating
    response data addressed to the peer into P2P-DI/1.0 protocol.

    Args:
        status_code: status code indicates of the success or failure
                     of the request. Based on HTTP status code.
        phrase: phrase indicates the additional information of the
                failure of the request or its success. Based on HTTP status
                code.
        cookie: integer a unique identifier of the peer.
        list_active_peers: list of active peers at the current moment.

    Returns:
        Protocol that contains response message addressed to the peer.
    """
    header = PROTOCOL + STATUS_CODE_PHRASE.format(status_code, phrase)
    protocol = header
    if status_code in [200, 201] and cookie is not None:
        protocol += PROTOCOL_COOKIE.format(cookie)
    elif status_code == 302:
        active_peers = ''
        for dict_active_peer in list_active_peers:
            host, port = dict_active_peer.items()[0]
            active_peers += PROTOCOL_ACTIVE_PEERS.format(host, port)
        protocol += active_peers
    protocol += PROTOCOL_EOP
    return protocol


def do_show():
    """Displays/prints all peers that have registered with this Register
    Server.

    Request comes from the user while it continuously prompts for request.
    The output displays all possible information about each registered peer.
    """
    if dict_peers:
        print 'Show: Each Registered Peer Information...'
        for key, peer in dict_peers.iteritems():
            peer.is_active()
            print key, ' ==> ', 'Hostname: {} '.format(peer.hostname), \
                'Port: {} (RFC Server) '.format(peer.port), \
                'Cookie: {} '.format(peer.cookie), \
                'Flag: {} '.format(peer.flag), \
                'TTL: {} '.format(int(peer.ttl)), \
                'Most Recent Registration Date: {} '.format(peer.reg_date), \
                'Times host been registered for last 30 days: {} '.format(
                    len(peer.reg_times))
    else:
        print 'No Registered Peers are found'

# The actual program starts here.
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

# Dictionary of all peers in the system that were registered.
# Mapping: {Cookie : Peer(IP, Port, Cookie, TTL, ...) object}.
dict_peers = {}

# Create and start new thread that takes care of the all requests coming from
#  different peers to a welcoming port of the Register Server.
peer_requests_thread = PeerRequests()
peer_requests_thread.start()

# User-driven - prompts user for commands.
while True:
    command = raw_input('> ').upper()
    command_fields = command.split(' ')
    request = command_fields[0]
    if request == 'SHOW':
        do_show()
    elif request == 'EXIT':
        print 'Stopping Register Server...'
        server_socket.shutdown(SHUT_RDWR)
        server_socket.close()
        del server_socket
        peer_requests_thread.join()
        exit('Goodbye')
    elif request == 'HELP':
        try:
            with open('help_registration_server.txt', 'r') as fin:
                print fin.read()
        except Exception as e:
            print e.__doc__, type(e).__name__, e.message
            print 'File \'help_registration_server.txt\' not found. ' \
                  'Please import file in local directory!'
    elif request == '':
        pass
    else:
        print 'Command not found. Use \'help\' to see proper commands.\n'
