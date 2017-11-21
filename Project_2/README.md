# Point-to-Multipoint File Transfer Protocol (P2MP-FTP)
## CSC 573 (601) - Internet Protocols
P2MP-FTP - protocol that provides a FTP sophisticated service: transferring a file from one host (p2mp client) to multiple destinations (p2mp servers). P2MP-FTP uses UDP to send packets from the sending host (p2mp client) to each of the destinations (p2mp servers) as opposed to the traditional FTP where TCP is used to ensure reliable data transmission of files from one sender to one receiver. In order to provide reliable data transfer service, P2MP-FTP utilizes the Stop-and-Wait automatic repeat request (ARQ). Hence, using the unreliable UDP protocol, P2MP-FTP allows implementation of a transport layer service such as reliable transfer in user space.
## Run P2MP-FTP Client (Sender) program
To execute the P2MP-FTP Client (Sender) program run:
```
 python ngtitov_p2mpclient.py arg1 arg2 ... arg(i) arg(i+1) arg(i+2) arg(i+3)
 ```
 where at least 4 (four) arguments are required and specified as follows:
 *	arg1, arg2, . . . , arg(i):

    Host name(s) or IPv4 address(es) of the Server(s). Can take any number of servers.
 *  arg(i+1):

    Port number of the Server(s) to which the Server(s) is listening. All Servers must listen on the same port number. The port number must be in the range of allowed ports `(1024, 65535]`. The firewall on the Servers must be disabled.
 *  arg(i+2):

    Name of the file to be transmitted. Any type of the file is acceptable.
 *  arg(i+3):
 
    Maximum segment size (MSS) in bytes. MSS must be greater than the header size (8 bytes), but less than 2048 bytes.
    
Example of the P2MP-FTP Client (Sender) program execution:
```
 python ngtitov_p2mpclient.py 152.46.17.179 152.46.17.182 152.46.17.192 7735 update.txt 1000
 ```
## Run P2MP-FTP Server (Receiver) program
To execute the P2MP-FTP Server (Receiver) program run:
```
 python ngtitov_p2mpserver.py arg1 arg2 arg3
 ```
 where all 3 (three) arguments are required and specified as follows:
 *  arg1:
 
    Port number of the Server to which the Server is listening. The port number must be in the range of allowed ports `(1024, 65535]`. The firewall on the Servers must be disabled.
 *  arg2:
 
    Name of the file where the data will be written.
 *  arg3:
 
    Packet loss probability. It must be in the range of `0 <= p <= 1`, where 0 is 0% packet loss and 1 is 100% packet loss.

Example of the P2MP-FTP Server (Receiver) program execution:
```
python ngtitov_p2mpserver.py 7735 new_update.txt 0.5
```
## Environment specifications and Prerequisites
The project is implement in Python language. For successful run please ensure following prerequisites are met:
*  Python version >= 2.7
*  Operating System: any Linux distribution (Ubuntu, RedHat, etc) that has Python version >= 2.7
*  Firewall on the P2MP-FTP Server(s) must be disabled
*  Port number of the P2MP-FTP Servers to which the servers are listening must
   *  Listen on the same port number
   *  Be in the range of allowed ports `(1024, 65535]`
## P2MP-FTP Stop-and-Wait ARQ protocol
P2MP-FTP Stop-and-Wait ARQ protocol for Data Packet is defined as follows:
```
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
```
P2MP-FTP Stop-and-Wait ARQ protocol for ACK is defined as follows:
```
0                      16                      32
-------------------------------------------------    -
|              ACKed Sequence Number            |     |
-------------------------------------------------     |--> 8 bytes
|        0x0000         |  ACK Packet Indicator |     |
-------------------------------------------------    -
```
Where each field is defined as follows:
*  Sequence Number:
   
   The sequence number of the first byte in the data field. It always starts from 0.
*  Checksum:
   
   It is computed in the same way as the UDP checksum described in the text book, J. F. Kurose and K. W. Ross, Computer Networking, 7th ed., Pearson. ISBN: 0-13-359414-9 in the section 3.3.2 on page 202. UDP at the sender side performs the 1s complement of the sum of alt the 16-bit words in the segment, with any overflow encountered during the sum being wrapped around. This result is put in the checksum field of the segment. At the receiver, all four 16-bit words are added, including the checksum. If no errors are introduced into the packet, then clearly the sum at the receiver will be `1111111111111111`. If one of the bits is a 0, then we know that errors have been introduced into the packet.
*  Data Packet Indicator:

   It may have two different values indicating a data packet.
   *  `0101010101010101` value indicates the non-last sequenced data packet to be transmitted/received
   *  `0101010101010111` value indicates the last sequenced data packet to be transmitted/received
* Payload:

  The actual payload or data of the file being transmitted.
*  ACKed Sequence Number:

   The sequence number of the next byte of data that the P2MP-FTP Server (Receiver) is expecting/waiting for
*  ACK Packet Indicator:

   It has the value `1010101010101010` is the indication of an ACK packet.

## Contributing
Please contact the author for any contributions.
## Authors
* **Nikolay G. Titov**
