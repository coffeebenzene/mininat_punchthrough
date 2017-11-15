import argparse
import socket
import threading
import time

class AtomicVariable():
    """For extra security"""
    
    def __init__(self, initial_value=None):
        self._lock = threading.Lock()
        self._value = initial_value
    
    def set(self, value):
        with self._lock:
            self._value = value
        return value
    
    def get(self):
        with self._lock:
            value = self._value
        return value



def keepalive(sock, ka_box, do_keepalive):
    """Thread function. Send keepalives to specified address every 10s."""
    while do_keepalive.get():
        payload, address = ka_box.get()
        sock.sendto(payload, address)
        time.sleep(10)

def main(room_id=0, server_address=("3.0.0.2",80)):
    if not (0 <= room_id <= 999999):
        raise ValueError("Room ID must be a 6 digit number (0-999999).")
    room_id = "{:06}".format(room_id)
    
    # UDP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsocktimeout(5.0)
    
    # Start keepalive and server request
    ka_box = AtomicVariable((room_id, server_address))
    do_keepalive = AtomicVariable(True)
    ka_thread = threading.thread(target=keepalive, args=(s, ka_box, do_keepalive))
    # Keepalive is also the request to server for connection. Until ka_box is changed.
    ka_thread.start()
    
    # Server response format:
    # {requester ip}\n{requester port}\n{other ip}\n{other port}\n{random key}
    while True:
        data, address = s.recvfrom(65507)
        if address == server_address:
            break
    
    data = data.split("\n")
    my_addr = (data[0], int(data[1]))
    other_addr = (data[2], int(data[3]))
    punch_key = data[4]
    
    state = 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ip', type=str, default="3.0.0.2", help='Server ip')
    parser.add_argument('-p', '--port', type=int, default=80, help='Server port')
    parser.add_argument('room', type=int, default=0, help='Room ID')
    args = parser.parse_args()
    server_address = (args.ip, args.port)
    
    main(args.room, server_address)