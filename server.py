import argparse
import random
import socket
import time
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# mapping of {room_id : [address, timeout]}
room_map = {}
running = True

def cleanup():
    current_time = time.time()
    timed_out = [k for k,v in room_map.iteritems() if v[1]<current_time]
    for rm_id in timed_out:
        del room_map[rm_id]

def main(args):
    # UDP socket
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.bind((args.ip,args.port))
    sock.settimeout(1) # Timeout so that will loop and do cleanup
    
    room_timeout = args.timeout
    while True:
        cleanup()
        try:
            room_id, address = sock.recvfrom(6) # Receive 6 digit room id.
        except socket.timeout:
            continue
        
        if room_id not in room_map: # New request
            room_map[room_id] = [address, time.time() + room_timeout]
            logger.info("First host for room_id {} : {}".format(room_id, room_map[room_id]))
        elif room_map[room_id][0] == address: # Repeated request (update timeout)
            room_map[room_id][1] = time.time() + room_timeout
            logger.info("Updated timeout for room_id {} : {}".format(room_id, room_map[room_id]))
        elif time.time() > room_map[room_id][1]: # 2nd host request but timed out.
            logger.info("Timed-out for room_id {} : {}".format(room_id, room_map[room_id]))
            del room_map[room_id]
        else: # 2nd host request. (accepted)
            logger.info("<LINK> Accepted 2nd host for room_id {} : {} | host2:{}".format(room_id, room_map[room_id], address))
            # Generate the key
            key = random.randint(0,99999999)
            key = "{:08}".format(key)
            logger.info("<LINK> Generated key:{}".format(key))
            # Generate data to send
            host1_addr = room_map[room_id][0]
            host2_addr = address
            host1_data = [host1_addr[0], str(host1_addr[1]), host2_addr[0], str(host2_addr[1]), key]
            host1_data = "\n".join(host1_data)
            host2_data = [host2_addr[0], str(host2_addr[1]), host1_addr[0], str(host1_addr[1]), key]
            host2_data = "\n".join(host2_data)
            # Send data
            sock.sendto(host1_data, host1_addr)
            sock.sendto(host2_data, host2_addr)
            # Room is used, remove room.
            del room_map[room_id]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ip', type=str, default="3.0.0.2", help='Server ip')
    parser.add_argument('-p', '--port', type=int, default=80, help='Set Server Port')
    parser.add_argument('-t', '--timeout', type=int, default=30, help='Set timeout for room ids in seconds')
    args = parser.parse_args()
    main(args)
