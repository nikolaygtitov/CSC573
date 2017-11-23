"""
ngtitov_p2mpserver.py

CSC 573 (601) - Internet Protocols
Project 2
This program implements the solution the Project 2 assignment:
Point-to-Multipoint File Transfer Protocol (P2MP-FTP).

P2MP-FTP - protocol that provides a FTP sophisticated service: transferring a
file from one host (p2mp client) to multiple destinations (p2mp servers).
P2MP-FTP uses UDP to send packets from the sending host (p2mp client) to each
of the destinations (p2mp servers) as opposed to the traditional FTP where
TCP is used to ensure reliable data transmission of files from one sender to
one receiver. In order to provide reliable data transfer service, P2MP-FTP
utilizes the Stop-and-Wait automatic repeat request (ARQ). Hence, using the
unreliable UDP protocol, P2MP-FTP allows implementation of a transport layer
service such as reliable transfer in user space.

This is P2MP-FTP Server (Receiver) implementation.
It starts listening on the well-known port specified by user in the command
line. When it receives a data packet, it computes the checksum and checks
whether it is in-sequence, and does the following:
 - If checksum is correct and it is in-sequence, it sends an ACK segment (
   using UDP) to the client and then writes the received data into a file whose
   name is provided in the command line.
 - If the packet received is out-of-sequence, an ACK for the last received
   in-sequence packet is sent.
 - If the checksum is incorrect, it does nothing.

Execute the program run:
 > python ngtitov_p2mpserver.py arg1 arg2 arg3
 where all 3 (three) arguments are required
 - arg1: Port number of the Server
 - arg2: Name of the file
 - arg3: Packet loss probability


@version: 1.0
@todo: None
@since: November 01, 2017

@status: Complete
@requires: None

@contact: ngtitov@ncsu.edu
@author: Nikolay G. Titov
"""

# Import required Python libraries
from socket import *
from random import *
import sys
import os

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
LAST_DATA_PACKET = 0b0101010101010111
ACK = 0b1010101010101010
HEADER_SIZE = 8
MAX_MSS = 2048
USAGE = 'usage: ngtitov_p2mpserver.py arg1 arg2 arg3\n\n        ' \
        'arg1: Port number of the Server to which server is listening\n      ' \
        '  arg2: Name of the file where the received data is written into\n  ' \
        '      arg3: Packet loss probability must be in range of [0, 1]'


def rdt_receive():
    """Receives and handles data packets from the P2MP-FTP Client.

    It receives the data packet, decides whether it needs to discard or
    process it based on probability value. It contains infinite loop and the
    only way to stop it is Keyboard Interrupt - <Ctrl c>.
    """
    server_socket = socket(AF_INET, SOCK_DGRAM)
    file_out = open(file_name, 'wb')
    try:
        server_socket.bind(('', server_port))
        seq_number = 0
        print 'P2MP-FTP Server is initialized and listing ...'
        receive = True
        while receive:
            datagram, client_address = server_socket.recvfrom(MAX_MSS)
            random_number = random()
            # Discard (r <= p) or process received packet (r > p)
            if probability < random_number:
                # Process the data packet
                header = datagram[:HEADER_SIZE]
                payload = datagram[HEADER_SIZE:]
                # Do validation on checksum, data indicator and sequence number
                new_seq_number = validation(header, payload, seq_number)
                # Send response only if packet is received correctly or
                # received out of sequence
                if new_seq_number is not None:
                    # Construct the ACK and send it back to the client
                    ack_packet = ack_encapsulation(seq_number)
                    server_socket.sendto(ack_packet, client_address)
                    if new_seq_number != seq_number:
                        # Update sequence number and write payload to the file
                        seq_number = new_seq_number
                        file_out.write(payload)
                        # Check if this is the last packet in sequence
                        if int(header[6:8].encode('hex'), 16) == \
                                LAST_DATA_PACKET:
                            receive = False
        print 'Complete!'
    except error, (value, message):
        print 'Exception while creating and binding RFC Server socket:'
        print message
    except KeyboardInterrupt:
        print 'Not completed. Goodbye!'
    file_out.close()
    server_socket.close()
    del server_socket


def validation(header, payload, seq_number):
    """Performs validation on the received packet.

    It extracts sequence number, checksum and indicator from the header of
    the received data packet and perform validation on each filed to ensure
    this expected data packet.

    Args:
        header: the header of the datagram - 64 bits (8 bytes)
        payload: payload that needs to be written into the file
        seq_number: expected sequence number to verify in-sequence order

    Returns:
        - Next expected sequence number (seq_number + segment length)
          If validation is successful and packet is in-sequence order
        - Current sequence number
          If packet is out-of-sequence
        - None
          If validation fails (checksum or not P2MP-FTP protocol)
    """
    rcv_seq_number = int(header[:4].encode('hex'), 16)
    rcv_checksum = int(header[4:6].encode('hex'), 16)
    rcv_indicator = int(header[6:8].encode('hex'), 16)
    # Split 32-bit sequence number into two 16-bit numbers
    # Initialize checksum with right-most 16 bits of sequence number
    checksum = rcv_seq_number & 0xffff
    rcv_seq_num_left_bits = rcv_seq_number >> 16
    # Add checksum with left-most 16 bits of sequence number, received
    # checksum and data packet indicator
    checksum = wrap_around(checksum, rcv_seq_num_left_bits)
    checksum = wrap_around(checksum, rcv_checksum)
    checksum = wrap_around(checksum, DATA_PACKET)
    # Add received payload (file content) into checksum
    for i in range(0, len(payload), 2):
        try:
            word = ord(payload[i]) + (ord(payload[i + 1]) << 8)
        except IndexError:
            word = ord(payload[i]) + (0 << 8)
        checksum = wrap_around(checksum, word)
    # Validate each field
    try:
        assert rcv_indicator in [DATA_PACKET, LAST_DATA_PACKET], \
            'Packet dropped, not a data packet'
        assert checksum == 0xffff, \
            'Packet is corrupted, dropping it [checksum = {}]'.format(
                bin(checksum).lstrip('-0b').zfill(16))
    except AssertionError, _e:
        print _e
        return None
    try:
        assert seq_number == rcv_seq_number, \
            'Packet loss, sequence number = {}'.format(rcv_seq_number)
    except AssertionError, _e:
        print _e
        return seq_number
    # Compute next expected sequence number
    new_seq_number = rcv_seq_number + len(header) + len(payload)
    if new_seq_number > 0xffffffff:
        new_seq_number = new_seq_number - 0xffffffff
    return new_seq_number


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


def ack_encapsulation(seq_number):
    """Encapsulates data into ACK packet that will be sent to P2MP-FTP Client.

    Args:
        seq_number: ACKed sequence number

    Returns:
        ACK packet ready to send back to P2MP-FTP Client
    """
    seq_number_hex = hex(seq_number).lstrip('-0x').zfill(8)
    seq_number_hex = seq_number_hex.decode('hex')
    zero_field_hex = hex(0).lstrip('-0x').zfill(4)
    zero_field_hex = zero_field_hex.decode('hex')
    ack_indicator = hex(ACK).lstrip('-0x').zfill(4)
    ack_indicator = ack_indicator.decode('hex')
    return seq_number_hex + zero_field_hex + ack_indicator


# Actual program starts here
try:
    # Validation of all arguments received from command line
    assert len(sys.argv) == 4, 'Error: Wrong number of arguments...\n'
    assert sys.argv[1].isdigit(), \
        'Error: Port number of the Server provided to which server must ' \
        'listen: \'{}\' is not Integer type...\n'.format(sys.argv[1])
    server_port = int(sys.argv[1])
    assert 1024 < server_port <= 0xffff, \
        'Port number must be in rage of (1024, 65535]\n'
    file_name = sys.argv[2]
    assert not os.path.isfile(file_name), \
        'Exception: \'{}\' file already exists, consider giving ' \
        'different name or removing file...\n'.format(file_name)
    probability = float(sys.argv[3])
    assert 0 <= probability <= 1, \
        'Exception: Packet loss probability must be in range of [0, 1]\n'
    # Start listening on well-known port
    rdt_receive()
except AssertionError, e:
    print e, USAGE
except ValueError, e:
    print e
    print 'Exception: Packet loss probability argument provided: \'{}\' is ' \
          'neither of Integer nor Float type, it must be integer or float in ' \
          'range of [0, 1]'.format(sys.argv[3])
