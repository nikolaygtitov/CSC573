"""
ngtitov_p2mpclient.py

CSC 573 (601) - Internet Protocols
Project 2
This program implements the solution the Project 2 assignment:
Point-to-Multipoint File Transfer Protocol (P2MP-FTP).

P2MP-FTP - protocol that provides a simple service: transferring a file from
one host (p2mp client) to multiple destinations (p2mp servers).P2MP-FTP uses
UDP to send packets from the sending host (p2mp client) to each of the
destinations (p2mp servers). In order to provide reliable data transfer
service, it utilizes the Stop-and-Wait ARQ.

This is P2MP-FTP Client (Sender) implementation.
It reads data from a file specified in the command line and utilizes reliable
data transfer (Stop-and-Wait ARQ) to transfer the data to the P2MP-FTP
Servers. Dat from file is provided on a byte basis. It also implements the
sending side of the reliable Stop-and-Wait protocol by ensuring that the data
is received correctly at the Servers. It reads the value of the maximum
segment size (MSS) from the command line. The Stop-and-Wait protocol buffers
the data until it has at least one MSS worth of bytes. At that time it forms
a segment that includes a header and MSS bytes of data; as a result,
all segments sent, except possibly for the very last one, will have exactly
MSS bytes of data. The client transmits each segment separately to each of
the receivers, and waits until it has received ACKs from every receiver
before it can transmit the next segment. Every time a segment is
transmitted, the sender sets a timeout counter. If the counter expires before
ACKs from all receivers have been received, then the sender re-transmits the
segment, but only to those receivers from which it has not received an ACK
yet. This process repeats until all ACKs have been received.

Execute the program run:
 > python ngtitov_p2mpclient.py arg1 arg2 ... arg(i) arg(i+1) arg(i+2) arg(i+3)
 where at least 4 (four) arguments are required
 - arg1, arg2, ..., arg(i): Host name(s) or IPv4 address(es) of the Server(s)
 - arg(i+1): Port number of the Server(s)
 - arg(i+2): Name of the file to be transmitted
 - arg(i+3): Maximum segment size (MSS)


@version: 1.0
@todo: None
@since: November 01, 2017

@status: Complete
@requires: Existing file with the name specified in the command line with
           content to be transmitted

@contact: ngtitov@ncsu.edu
@author: Nikolay G. Titov
"""

# Import required Python libraries
from socket import *
import sys
import os
import requests
import time

# P2MP-FTP Stop-and-Wait ARQ protocol for Data Packet is defined:
"""
0                      16                      32
-------------------------------------------------    -
|                Sequence Number                |     |
-------------------------------------------------     |
|        Checksum       | Data Packet Indicator |     |
-------------------------------------------------     |--> MSS
|                                               |     |
|                    Payload                    |     |
|                                               |     |
-------------------------------------------------    -
"""

# P2MP-FTP Stop-and-Wait ARQ protocol for ACK is defined:
"""
0                      16                      32
-------------------------------------------------    -
|              ACKed Sequence Number            |     |
-------------------------------------------------     |--> 8 bytes
|        0x0000         |  ACK Packet Indicator |     |
-------------------------------------------------    -
"""

# Initialization of constants
DATA_PACKET = 0b0101010101010101
ACK = 0b1010101010101010
HEADER_SIZE = 8
MAX_MSS = 2048
ACK_SIZE = 8
USAGE = 'usage: ngtitov_p2mpclient.py arg1 arg2 ... arg(i) arg(i+1) arg(i+2) ' \
        'arg(i+3)\n\n        arg1, arg2, ..., arg(i): Host name(s) or IPv4 ' \
        'Address(es) of the Server(s) (receiver(s)) 1, 2, ..., i\n        ' \
        'arg(i+1):                Port number of the Server(s)\n        arg(' \
        'i+2):                Name of the file to be transferred\n        ' \
        'arg(i+3):                Maximum segment size (MSS)'


def rdt_send():
    """Gathers all P2MP-FTP protocol data fields together to make up a datagram
    of 1 MSS and send it to the list of P2MP-FTP Servers.

    Reads enough raw from the file to build 1 MSS packet worth of data. Calls
    helper functions to calculate checksum (sum of all 16 bit words and take
    complement of it), construct the header and transmit the packet.
    """
    seq_number = 0
    file_in = open(file_name, 'rb')
    payload = file_in.read(mss - HEADER_SIZE)
    try:
        while payload:
            if seq_number > 0xffffffff:
                seq_number = seq_number - 0xffffffff
            # Get the checksum and header
            checksum = get_checksum(seq_number, payload)
            header = get_header(seq_number, checksum)
            retransmit = True
            # Continuously retransmit the same datagram until all P2MP-FTP
            # Servers received it
            while retransmit:
                retransmit = rdt_send_datagram(header + payload, seq_number)
            # Get header field for the next packet
            payload = file_in.read(mss - HEADER_SIZE)
            seq_number = seq_number + mss
    except KeyboardInterrupt:
        pass
    file_in.close()


def get_checksum(seq_number, payload):
    """Calculates checksum of the data that will be send to the P2MP-FTP Servers

    Calculation is performed by adding all 16 bit words of sequence number,
    data packet indicator, and payload performing wrap around if overflow
    occurs and takes complement of it.

    Args:
        seq_number: sequence number of the packet that will be transmitted
        payload: raw binary data of the file content that will be transmitted

    Returns:
        Checksum of the packet
    """
    # Split 32-bit sequence number into two 16-bit numbers
    # Initialize checksum with right-most 16 bits of sequence number
    checksum = seq_number & 0xffff
    seq_num_left_bits = seq_number >> 16
    # Add checksum with left-most 16 bits of sequence number and data packet
    # indicator
    checksum = wrap_around(checksum, seq_num_left_bits)
    checksum = wrap_around(checksum, DATA_PACKET)
    # Include payload (file content) into checksum
    for i in range(0, len(payload), 2):
        try:
            word = ord(payload[i]) + (ord(payload[i+1]) << 8)
        except IndexError:
            word = ord(payload[i]) + (0 << 8)
        checksum = wrap_around(checksum, word)
    return ~checksum & 0xffff


def wrap_around(a, b):
    """Performs wrap around on two 16-bit words if overflow occurs.

    Args:
        a: first 16-bit word
        b: second 16-bit word

    Returns:
        Result of the wrap around, a new 16-bit word
    """
    checksum = a + b
    return (checksum & 0xffff) + (checksum >> 16)


def get_header(seq_number, checksum, indicator=DATA_PACKET):
    """Converts sequence number, checksum, and data packet indicator integer
    numbers into hexadecimal byte representation to fit all header data into
    8 bytes as defined by P2MP-FTP protocol

    Args:
        seq_number: sequence number integer
        checksum: checksum integer
        indicator: by default data packet indicator

    Returns:
        8-byte header field in the hexadecimal byte representation
    """
    seq_number_hex = hex(seq_number).lstrip('-0x').zfill(8).decode('hex')
    checksum_hex = hex(checksum).lstrip('-0x').zfill(4).decode('hex')
    indicator_hex = hex(indicator).lstrip('-0x').zfill(4).decode('hex')
    return seq_number_hex + checksum_hex + indicator_hex


def rdt_send_datagram(datagram, seq_number):
    """Sends datagram to all the P2MP-FTP Servers via multi-cast.

    Create new UDP socket with timeout interval to transfer datagram to 2MP-FTP
    Servers. The multi-cast technique is used to send the same (one)
    datagram to all P2MP-FTP Servers. After datagram is sent to all P2MP-FTP
    Servers, it waits for ACK responses from P2MP-FTP Servers. Calls helper
    function to determine what P2MP-FTP Servers received data packets correctly.

    Args:
        datagram: datagram in a byte representation
        seq_number: expected sequence number ACKed by the P2MP-FTP Servers

    Returns:
        Boolean indicating whether retransmit is required or not
    """
    retransmit = False
    client_socket = socket(AF_INET, SOCK_DGRAM)
    client_socket.settimeout(timeout_interval)
    try:
        # Send datagram to P2MP-FTP Servers yet did not receive this datagram
        # using new UDP socket
        for name, host in dict_hosts.iteritems():
            # No need to retransmit datagram if server has already received it
            if host.ack != seq_number:
                retransmit = True
                client_socket.sendto(datagram, (name, server_port))
        # Read ACKs until timeout is triggered
        while retransmit:
            ack_packet, (server_ip, port) = client_socket.recvfrom(ACK_SIZE)
            dict_hosts[server_ip].ack_packet = ack_packet
    except timeout:
        print 'Timeout, sequence number = {}'.format(seq_number)
        # Determine what P2MP-FTP Servers received data packets correctly
        extract_servers_ack(seq_number)
    client_socket.close()
    del client_socket
    return retransmit


def extract_servers_ack(seq_number):
    """Extracts ACKs received from P2MP-FTP Servers as response.

    Args:
        seq_number: expected sequence number ACKed by the P2MP-FTP Servers
    """
    for name, host in dict_hosts.iteritems():
        if host.ack_packet is not None:
            # Extract received ACKed sequence number, zero field and ACK
            # indicator
            rcv_ack = int(host.ack_packet[:4].encode('hex'), 16)
            rcv_zero_field = int(host.ack_packet[4:6].encode('hex'), 16)
            rcv_ack_indicator = int(host.ack_packet[6:8].encode('hex'), 16)
            try:
                assert rcv_ack == seq_number
                assert rcv_zero_field == 0
                assert rcv_ack_indicator == ACK
                dict_hosts[name].ack = seq_number
            except AssertionError:
                pass


class Host:
    """P2MP-FTP Server object keeps record for each Server.

    Used for keeping track of the name of the P2MP-FTP Server, latest ACK
    packet received from P2MP-FTP Server, ACKs for the last successfully
    received in-sequence packet.

    Attributes:
        name: hostname of the P2MP-FTP Server
        ack_packet: content of the latest received ACK
        ack: ACK for the last successfully received in-sequence packet
    """
    def __init__(self, name):
        """Initiates Host object with default attributes."""
        self.name = name
        self.ack_packet = None
        self.ack = None


# Actual program starts here
# Initialize dictionary of host objects and timeout interval
dict_hosts = {}
timeout_interval = 0
try:
    # Validation of all arguments received from command line
    assert len(sys.argv) >= 5, 'Error: Wrong number of arguments...\n'
    assert sys.argv[-1].isdigit(), \
        'Error: Maximum Segment Size (MSS) provided: \'{}\' is not Integer ' \
        'type...\n'.format(sys.argv[-1])
    assert sys.argv[-3].isdigit(), \
        'Error: Port number of the Server(s) provided: \'{}\' is not Integer ' \
        'type...\n'.format(sys.argv[-3])
    mss = int(sys.argv[-1])
    server_port = int(sys.argv[-3])
    assert mss > HEADER_SIZE, \
        'Exception: Maximum Segment Size (MSS) provided: \'{}\' <= 8 bytes ' \
        'is not enough to encapsulate the payload into the ' \
        'segment...\n'.format(sys.argv[-1])
    assert MAX_MSS >= mss, \
        'Exception: Maximum Segment Size (MSS) provided: \'{}\' exceeds ' \
        'possible MSS value of 2048 bytes (consider smaller value for ' \
        'MMS)...'.format(sys.argv[-1])
    assert 1024 < server_port <= 0xffff, \
        'Port number must be in rage of (1024, 65535]\n'
    file_name = sys.argv[-2]
    assert os.path.isfile(file_name), \
        'Error: \'{}\' no such file...\n'.format(file_name)
    for h in range(1, len(sys.argv) - 3):
        # Create host object with the name, ACK response packet and ACK
        # sequence number. Store object into the dictionary of hosts
        if sys.argv[h] == 'localhost':
            hostname = '127.0.0.1'
        else:
            hostname = sys.argv[h]
        _host = Host(hostname)
        dict_hosts[hostname] = _host
        # Determine RTT to this host and adjust timeout accordingly
        start_time = time.time()
        try:
            http_request = requests.get('http://{}'.format(hostname))
            rtt = http_request.elapsed.total_seconds()
        except requests.exceptions.RequestException:
            rtt = time.time() - start_time
        if rtt > timeout_interval:
            timeout_interval = rtt
    # Start transferring data to P2MP-FTP Servers
    rdt_send()
except AssertionError, e:
    print e, USAGE
except ValueError, e:
    print e
