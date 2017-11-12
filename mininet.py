#!/usr/bin/env python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import info, setLogLevel
from mininet.cli import CLI
from mininet.node import OVSController

import os

setLogLevel('info')

class myTopo(Topo):
    """Topology for NAT punchthrough.
        S
        |
     ___R3___
    /        \
    R1(NAT)   R2(NAT)
    |         |
    h1        h2
    """
    
    def build(self): # Recommended method to overrider instead of __init__
        
        # Add clients (hosts).
        client1 = self.addHost('h1', ip='10.0.1.1/8')
        client2 = self.addHost('h2', ip='10.0.2.1/8')
        
        # Add nats (routers).
        nat1 = self.addHost('R1', ip='10.0.0.1/8')
        nat2 = self.addHost('R2', ip='10.0.0.1/8')
        self.addLink(client1, nat1)
        self.addLink(client2, nat2)
        
        # Add server
        server = self.addHost('S', ip='3.0.0.2/24')
        
        # Add internet simulator (Router).
        internet_sim = self.addHost('R3', ip='3.0.0.1/24')
        self.addLink(server, internet_sim)
        self.addLink(nat1, internet_sim,
                     intfName1="R1-eth1", intfName2="R3-eth1",
                     params1={"ip":"1.0.0.2/24"}, params2={"ip":"1.0.0.1/24"})
        self.addLink(nat2, internet_sim,
                     intfName1="R2-eth1", intfName2="R3-eth2",
                     params1={"ip":"2.0.0.2/24"}, params2={"ip":"2.0.0.1/24"})
        """Note about addLink(): 
        addLink() adds a edge to the topology, the subsequent named arguments
        depend on the Link class used when topology is added to the mninet 
        (which is the default Mininet Link).
        The Link object accepts intfName1, intfName2, and params1 and 2. params
        are the parameters for the respective interfaces, which use the mininet
        Intf class. params can accept mac, ip, ifconfig, up.
        """

def setup_mininet(net):
    # Set default gateways
    gw_map = {"h1": "10.0.0.1",
              "h2": "10.0.0.1",
              "R1": "1.0.0.1",
              "R2": "2.0.0.1",
              "S": "3.0.0.1",
             }
    for node, gw in gw_map.items():
        net.get(node).cmd("route add default gw {}".format(gw))
    
    # Set ip_forwarding for routers
    for node in net.hosts:
        if node.name.startswith("R"):
            node.cmd("sysctl net.ipv4.ip_forward=1")
    
    # Set nat. (In filter table, everything is allowed by default, so no need to set.)
    for nat_name in ["R1", "R2"]:
        nat = net.get(nat_name)
        nat.cmd("iptables -t nat -F POSTROUTING") # Flush just in case
        nat.cmd("iptables -t nat -A POSTROUTING -o {}-eth1 -j MASQUERADE".format(nat_name))



def main():
    # cleanup
    os.system("rm -f /tmp/R*.log /tmp/R*.pid logs/*")
    os.system("mn -c >/dev/null 2>&1")
    
    net = Mininet(topo=myTopo(), controller = OVSController)
    setup_mininet(net)
    net.start()
    info("Mininet started")
    
    #net.pingAll()
    #info("Mininet ping complete. (R3 cannot ping R1 and R2, because their default IP in mininet is 10.x.x.x)")
    
    CLI(net)
    net.stop()
    
    # cleanup
    os.system("rm -f /tmp/R*.log /tmp/R*.pid logs/*")
    os.system("mn -c >/dev/null 2>&1")



if __name__ == "__main__":
    main()