# 50.012 Networks Project
# NAT punchthrough

This can be more easily read at https://github.com/coffeebenzene/mininat_punchthrough

## Group:
* Amish 1001614
* Sidney 1001525
* Eric 1001526
* Zanette 1001845

## Background
We are implementing NAT punchthrough through port-restricted conical NATs. This
NAT punchthrough will be done on mininet. (Symmetric NATs are significantly 
harder to punchthrough.)

NAT punchthrough allows a direct peer-to-peer connection for hosts behind NATs. 
In this project, the connection will be used for a chatroom between 2 hosts.

`X--R--internet`

In the above network, R is a NAT gateway. A packet from A to the internet will
have its source IP(A) and port(A) changed to IP(R) and port(R). R will then expect
a return packet with destination IP(R) and port(R).

NAT punchthrough works based on the ability to know IP(R) and port(R) so that an
external host can connect to A via R. Also, A has to send a packet out first, so
that the NAT translation (i.e. the "hole") is in place.

## Demo
Currently, NAT punchthrough has been accomplished in mininet. Raw messages and files can
be sent via a reliable application layer protocol on top of UDP.

The first 48 characters of a UDP packet is used as the header.

1. In terminal, start up mininet. `sudo python natnet.py`
2. In the mininet CLI, create xterm windows for the server and clients. "xterm S", "xterm h1", "xterm h2".
3. First, start the NAT intermediary server on S. `python server.py`
    a. server.py accepts 2 options:
    b. -i for the server ip (defaults to 3.0.0.2)
    c. -p for port (defaults to 80)
4. Next, start the clients on both h1 and h2. `python client.py [room_id]`
    a. client.py accepts 2 options and 1 positional argument.
    b. -i for the server ip (defaults to 3.0.0.2)
    c. -p for server port (defaults to 80)
    d. room_id positional argument (required, 6 digit number). room_id is used to match clients to each other. Clients will only be connected when they used the same room_id.
5. The `client.py` will open a GUI window to show the progress of connecting. Once connected, it means that the NAT punchthrough is successful. Then clients can send messages to each other.
6. To send a file, enter `>sendfile <filename>` where <filename> is the name of the file to send. The file will be pushed to the other client's currend directory.

In order to externally verify that the NAT punchthrough is working (so you know we are not cheating in the client.py), you can use the following on R1 and R2:

* wireshark to view the packets being sent and received.
* `conntrack -L` (or `-J`) to show the NAT translations.

## How it works (basic guide)

### NAT
iptables was used for the NAT. iptables NAT is a port-restricted conical NAT by 
default. This means that the same IP and port will be used for the same socket 
from a client (unless allocated elsewhere).

However, when allowing all connections (default policy), there is a pathological
case when a UDP packet is sent to an unassigned port on the NAT. The NAT will
reply with an ICMP port unreachable message. However, even though it is an ICMP
message that was sent, this connection is tracked and the previously unassigned
UDP port will become considered assigned. Then when the host behind the NAT sends
a packet it will be translated to a different IP and port on the NAT.
This makes the iptables NAT similar to a symmetric NAT, and very difficult to
punchthrough.

This case was bypassed by setting iptables to drop all unknown incomming packets.

### Server
The server is simply an intermediary server that sends the IP addresses and ports
to the clients that send a requests to it. This is how the client knows the other
client's IP(R) and port(R) (from above).

### Client
The client first sends a request to the server, and receives the NATted IP
address and port of the other client.

Then, the client sends packets to the other client's NATted Ip address and port.
When both clients are sending packets to each other, if the NAT uses the same
translation, the packets will appear as replies, and thus the packets will be
allowed through.

Once a round trip is confirmed, the client allows sending of messages on the chat.
The protocol used for the chat takes inspriation from TCP and is intended to
allow arbitarily large messages and reliable transport. (Not implemented yet.)

### Reliable Transport Protocol

The reliable transport protocol is an application layer protocol that is meant to be a reliable mode of transfer, but does not aim to maximise anything else, such as throughput or latency. It is not space efficient due to sending numbers in ASCII instead of binary bit and using longer names instead of numbers for nominal-valued states. This is done for readability.

The protocol uses a 48 byte header followed by the payload:
<table>
    <tr>
        <th>4 byte</th>
        <th>4 byte</th>
        <th colspan=2>8 byte</th>
    </tr>
    <tr>
        <td colspan=2>Random key</td>
        <td colspan=2>State</td>
    </tr>
    <tr>
        <td colspan=2>Sequence Number</td>
        <td colspan=2>ACK number</td>
    </tr>
    <tr>
        <td>Message type</td>
        <td>Fragment identifer</td>
        <td colspan=2>Fragment number</td>
    </tr>
    <tr>
        <td colspan=4>Payload<br><br></td>
    </tr>
</table>

#### Handshaking
The **random key** is a key given by the server S to both clients h1 and h2, after they connect. This key is used to identify packets related to the NAT punchthrough. Any packet not starting with the key is ignored.

The **state** is mainly used for the handshaking procedure.

During handshaking, each client repeatedly sends its a message containing its state. (During handshake, only the first 16 bytes are sent, i.e. only the key and state.) Upon receiving a message, it will change its state accordingly.

The state meaning is shown in the table below:

| State      | Meaning |
| ---------- | ------- |
| 0 INIT     | This client does not know anything about other client yet.
| 1 RECV-RDY | After receiving a state 0 message, state will change to 1. This client is able to receive messages from other client. |
| 2 SEND-RDY | After receiving a state 1 message, state will change to 2. Receiving state 1 means that the other client is able to receive messages from this client. Thus, it also means that this client is able to send messages. |

Once in state 2, the client can begin to send data.

Note that the state should only increase, and receiving a state 2 message for example, will set the client's state to 2 as well.
Also, if client follow the protocol, it should be impossible for 1 client to be in state 0 and another in state 2.

#### Reliable transport

The **sequence number** and **ACK number** are concepts borrowed TCP go-back-n algorithm. Instead of counting bytes sent and received, this counts messages sent and received. They range from 00000000 to 99999999 (i.e. % 100000000). For simplicity, this should start from 1. However, in the program, they start from 99999998 instead, to show that the program is able to handle overflow of sequence number and ACK number.

For easier implementation, the receiver makes an assumption that packets received are always in order. This is enforced by allowing only 1 packet to be sent by a client at a time (i.e. sliding window size is 1). The solution to this is to store the packets in a buffer to allow reordering (this is not done to save time in implementation).

Thus, if an ACK for a message is not received on time, the message will simply be resent.

#### Message processing

**Message type** is either `MSG ` or `FILE`. It determines what content the message has, and what to do with it. `MSG ` are chat messages and will be printed on the chat screen. `FILE` are files and will be download and saved.

#### Message Fragmentation

If a message is too large (>50000 bytes). The message will be split into fragments of 50000 bytes.

**Fragment identifer** is either `FULL` or `FRAG`. `FULL` indicates that the message is not fragmented. `FRAG` indicates that the message is fragmented.

**Fragment number** is a 8 digit number that states the end of the group of fragments. After a large message is split into fragments, the sequence number of the last fragment will be calculated. This is the fragment number.

E.g. The current sequence number (last sent) is 99999998, a 180KB message is to be sent. 180KB requires 4 fragments. Thus, the final sequence number will be (99999998+4)%100000000 = 00000002. This is the fragment number.

#### Keepalive

In order to prevent the NAT from timing out the translation entry, each client will continously send keepalives messages periodically (10s). These messages send no data, and do not count in the acknowledgements. Their sequence number is fixed at 00000000.

Since the keepalive messages have to be continously sent, they are used to send the ACK responses. The timings are adjusted when receiving and sending data to ensure prompt ACK responses, and also not an excessive amount of keepalive messages are sent (e.g. if a message was just sent, then a keepalive message is not needed).
