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
*	[help_peer](https://github.ncsu.edu/ngtitov/CSC573/blob/master/Project_1/help_peers) file must be at the same location (directory) where `ngtitov_peers.py` program is executed
*	[help_registration_server](https://github.ncsu.edu/ngtitov/CSC573/blob/master/Project_1/help_registration_server) file must be in the same location (directory) where `ngtitov_registration_server.py` program is executed
*	User must have distinct directory (file space) where his/her RFC files is kept. Note that no other files are permitted in the same file space except RFC files
### Restrictions:
*	All RFC files initially taken from the [IETF](http://www.ietf.org/) web site and then kept at each peer's file space must ...
    * Be in ASCII format (.text files)
    * Follow their given (standard) naming convention by IETF (Ex: `rfc8210.txt`). Thus, __rfc__ prefix must be followed by the number (index) of the RFC
    * Not be modified
*	The IP address of the register server is hard-coded as localhost. In order to change the IP address of the Register server
    * Open `ngtitov_peers.py`
    * Search for `SERVER_IP` definition
    * Change it to IP address of desired Register Server
* __DO NOT__ stop either program by `\<Ctrl c\>`. Both programs are multi-threaded. Use `exit` command to stop all threads.
## P2P-DI/1.0 protocol
For this project, specific application layer protocol is defined for the Register Server and peers to communicate among themselves.
### Peer-to-Register Server P2P-DI/1.0 protocol communication protocol
Peer-to-Register Server __REQUEST__ message format is defined as follows:
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
Register Server-to-Peer __RESPONSE__ message format in response for `POST REGISTER` or `POST KEEPALIVE` request messages is defined as follows:
```
-----------------------------------------------------
| Protocol name and version | Status Code | Phrase  |
-----------------------------------------------------
|         Cookie:           |        Integer        |
-----------------------------------------------------
|                EOP (End of Protocol)              |
-----------------------------------------------------
```
Register Server-to-Peer __RESPONSE__ message format in response for `GET PQUERY` request message is defined as follows:
```
-----------------------------------------------------
| Protocol name and version | Status Code | Phrase  |
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
Register Server-to-Peer __RESPONSE__ message  format in response for `POST LEAVE` request message is defined as follows:
-----------------------------------------------------
| Protocol name and version | Status Code | Phrase  |
-----------------------------------------------------
|                EOP (End of Protocol)              |
-----------------------------------------------------
### Peer-to-Peer (RFC Server-to-Peer and Peer-to-RFC Server) P2P-DI/1.0 communication protocol
Peer-to-RFC Server (another peer) `GET RFC-INDEX` __REQUEST__ message format is defined as follows:
```
----------------------------------------------
| Type  | Method | Protocol name and version |
----------------------------------------------
| Host: |  IPv4  |   Port:    |   Integer    |
----------------------------------------------
|      OS:       |          System           |
----------------------------------------------
| Date: |  Year-Month-Day Hour-Min-Sec-mSec  |
----------------------------------------------
|         EOP (End of Protocol)              |
----------------------------------------------
```
Peer-to-RFC Server (another peer) `GET RFC` __REQUEST__ message format is defined as follows:
```
------------------------------------------------------
| Type  | Method | Index | Protocol name and version |
------------------------------------------------------
| Host: |  IPv4  | Port: |          Integer          |
------------------------------------------------------
|      OS:       |              System               |
------------------------------------------------------
|     Date:      | Year-Month-Day Hour-Min-Sec-mSec  |
------------------------------------------------------
|               EOP (End of Protocol)                |
------------------------------------------------------
```
RFC Server-to-peer __RESPONSE__ message format in response for `GET RFC-INDEX` request message is defined as follows:
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
RFC Server-to-Peer __RESPONSE__ message format in response for `GET RFC` request message is defined as follows. Note that protocol itself comes as plane text, but the requested RFC document in the binary mode:
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
