# Peer-to-Peer with Distributed Index (P2P-DI) System for Downloading RFCs
## CSC 573 (601) - Internet Protocols 
In the traditional network system, one centralized server is utilized for downloading RFCs. This project offers a Peer-to-Peer with distributed index (P2P-DI) system in which peers may download desired RFCs that currently are not in their hard drive (or file space), directly from other active peers in the P2P-DI system. There is one Registration Server that runs on well-known IP address (can be changed by the user) and port - 65423. The Registration Server maintains information about all active peers in the P2P-DI system that have registered with it. Peers learn about other peers in the P2P-DI system via the Registration Server by sending request messages to it upon their registration. All communication among peers and registration server takes place over TCP and strictly under P2P-DI/1.0 application protocol.
## Running Registration Server and Peer programs:
To start Registration Server:
```
python ngtitov_registration_server.py
```
Note that Peer program assumes that Register Server runs at localhost, to change it - see Restrictions below.
To start Peer program:
```
python ngtitov_peers.py
```
Both the Registration Server and Peer programs are user-driven and both programs continuously prompt the user for commands.
To see the list of commands for both programs:
```
> help
``` 
Peer program supports multiple commands. Please read description for each command.

Once the ngtitov_peers.py program started, the user is prompted to enter his/her file system where RFC pages (files) are kept:
```
> Please specify YOUR own file space (directory):
```
If ngtitov_peers.py command is unable to determine the IP address of the host, it prompts the user to enter one:
```
Warning: Program unable to determine IP address of the host you are running on...
> Please specify the IP address of your host:
```
IPv4 addresses or localhost are accepted.
### Language:
Python
### Prerequisites:
*	Python version >= 2.7
*	[help_peer](https://github.ncsu.edu/ngtitov/CSC573/blob/master/Project_1/help_peers) file must be at the same location (directory) where __ngtitov_peers.py__ program is executed.
*	[help_registration_server](https://github.ncsu.edu/ngtitov/CSC573/blob/master/Project_1/help_registration_server) file must be in the same location (directory) where __help_registration_server.py__ program is executed
*	User must have distinct directory (file space) where his/her RFC files is kept. Note that no other files are permitted in the same file space except RFC files
### Restrictions:
*	All RFC files initially taken from the [IETF](http://www.ietf.org/) web site and then kept at each peer's file space must be in ASCII format (.text files)
*	The IP address of the register server is hard-coded as localhost. In order to change the IP address of the Register server
    * Open __ngtitov_peers.py__
    * Search for __SERVER_IP__ definition
    * Change it to IP address of desired Register Server
* __DO NOT__ stop either program by __\<Ctrl c\>__. Both programs are multithreaded. Use __exit__ command. 
## P2P-DI/1.0 protocol
For this project, specific application layer protocol is defined for the Register Server and peers to communicate among themselves.
### Peer-to-Register Server P2P-DI/1.0 protocol communication protocol
Peer-to-Register Server __REQUEST__ message is defined as follows:
```
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
```
Register Server-to-Peer __RESPONSE__ message is defined as follows:
```
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
```
### Peer-to-Peer (RFC Server) P2P-DI/1.0 protocol communication protocol
Peer-to-RFC Server (another peer) __REQUEST__ message is defined as follows:
```
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
```
RFC Server-to-peer __RESPONSE__ message (based on GET RFC-INDEX request) is defined as follows:
```
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
```
RFC Server-to-peer __RESPONSE__ message (based on GET RFC \#)is defined as follows. Note that header protocol comes as plane text, but the requested RFC document itself in the binary mode:
```
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
```
## Contributing
Please contact the author for any contributions.
## Authors
* **Nikolay G. Titov**
