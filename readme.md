# 50.012 Networks Project
# NAT punchthrough

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

In the above network, R is a NATing gateway. A packet from A to the internet will
have its source IP(A) and port(A) changed to IP(R) and port(R). R will then expect
a return packet with destination IP(R) and port(R).

NAT punchthrough works based on the ability to know IP(R) and port(R) so that an
external host can connect to A via R. Also, A has to send a packet out first, so
that the NAT translation (i.e. the "hole") is in place.

## Demo
Currently, NAT punchthrough has been accomplished in mininet. Raw messages can
be sent via UDP on the chat. However, there is intended to be an Application layer
protocol to ensure reliable transport.

The reliable transport message protocol for the chat has not been fully implemented.
The first  32 characters will be truncated when receiving. Also, the "punch key"
needs to be entered as the first 8 characters of the message, or the message will
be dropped when receiving.

1. In terminal, start up mininet. `sudo python natnet.py`
2. In the mininet CLI, create xterm windows for the server and clients. "xterm S", "xterm h1", "xterm h2".
3. First, start the NAT intermediary server on S. `python server.py`
    a. server.py accepts 2 options:
    b. -i for the server ip (defaults to 3.0.0.2)
    c. -p for port (defaults to 80)
4. Next, start the clients on both h1 and h2. `python client.py`
    a. client.py accepts 2 options and 1 positional argument.
    b. -i for the server ip (defaults to 3.0.0.2)
    c. -p for server port (defaults to 80)
    d. room_id positional argument (defaults to 0). room_id is used to match clients to each other. Clients will only be connected when they used the same room_id.
5. The `client.py` will open a GUI window to show the progress of connecting. Once connected, it means that the NAT punchthrough is successful. Then clients can send messages to each other.

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
This makes the iptables NAT similar to a symmetric NAT, and very difficult to punchthrough.

### Server
The server is simply an intermediary server that sends the IP addresses and ports
to the clients that send a requests to it. This is how the client knows the other
client's IP(R) and port(R) (from above).

### Client
THe client first sends a request to the server, and receives the NATted IP
address and port of the other client.

Then, the client sends packets to the other client's NATted Ip address and port.
When both clients are sending packets to each other, if the NAT uses the same
translation, the packets will appear as replies, and thus the packets will be
allowed through.

Once a round trip is confirmed, the client allows sending of messages on the chat.
The protocol used for the chat takes inspriation from TCP and is intended to
allow arbitarily large messages and reliable transport.