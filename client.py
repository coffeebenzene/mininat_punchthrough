import argparse
import socket
import threading
import time
import logging

import Tkinter as tkr
import ttk
import ScrolledText

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

STATEMAP = {0:"    INIT",
            1:"RECV-RDY",
            2:"SEND-RDY",
            "    INIT":0,
            "RECV-RDY":1,
            "SEND-RDY":2,
           }

class Application(ttk.Frame):
    
    def __init__(self, master=None):
        ttk.Frame.__init__(self, master)
        
        self.textarea = ScrolledText.ScrolledText(self)
        self.textarea.grid(row=0, column=0, columnspan=2, sticky="NSEW")
        self.textarea.configure(state=tkr.DISABLED)
        
        self.input_val = tkr.StringVar()
        self.input_field = ttk.Entry(self, text = self.input_val)
        self.input_field.grid(row=1, column=0, sticky="SEW", pady=1)
        self.input_field.bind("<Return>", self.send)
        
        self.sendbtn = ttk.Button(self, text="Send", command=self.send, state=tkr.DISABLED)
        self.sendbtn.grid(row=1, column=1, sticky="NSEW", pady=1, padx=1)
        
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.grid(sticky="NSEW")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.master.title("NAT Punchthrough")
    
    def insert_text(self, text):
        self.textarea.configure(state=tkr.NORMAL)
        self.textarea.insert(tkr.END, text)
        self.textarea.insert(tkr.END, "\n")
        self.textarea.configure(state=tkr.DISABLED)
    
    def allow_sending(self, sock, dest_addr):
        self.sock=sock
        self.dest_addr = dest_addr
        self.sendbtn["state"] = tkr.NORMAL
    
    def send(self, event=None):
        print event # DEBUG

class socket_wrapper(object):
    
    def __init__(self, sock, dest_addr, punch_key):
        self.sock = sock
        self.dest_addr = dest_addr
        self.punch_key = punch_key
        self.state = 2
        self.seq_num = 0
        self.ack_num = 0
    
    def send(self, payload):
        msg = "" # NEED TO FIGURE OUT HOW TIMEOUT A SEND MESSAGE, so can retry sending.
        



# Threading related
class AtomicVariable(object):
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



def keepalive(sock, ka_box, ka_interval, next_time):
    """Thread function. Send keepalives to specified address every 10s."""
    while ka_interval.get() > 0:
        # Send keepalive/periodic message.
        payload, address = ka_box.get()
        sock.sendto(payload, address)
        
        # Set next keepalive
        next_time.set(time.time() + ka_interval.get())
        
        # Sleep until next keepalive, polling for changes in next_time every 1s.
        # (since python can't interrupt nicely.)
        while next_time.get() > time.time():
            sleeptime = next_time.get() - time.time()
            if sleeptime > 1:
                sleeptime = 1
            time.sleep(sleeptime)



# Main (Receiver thread.)
def main(room_id=0, server_address=("3.0.0.2",80)):
    if not (0 <= room_id <= 999999):
        raise ValueError("Room ID must be a 6 digit number (0-999999).")
    room_id = "{:06}".format(room_id)
    
    # Setup Application in another thread.
    app = Application(master=tkr.Tk())
    app_thread = threading.Thread(target=app.mainloop)
    
    # UDP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Setup keepalive variables
    ka_box = AtomicVariable((room_id, server_address))
    ka_interval = AtomicVariable(10)
    next_time = AtomicVariable(time.time())
    # Keepalive is also the request to server for connection. Until ka_box is changed.
    ka_thread = threading.Thread(target=keepalive, args=(s, ka_box, ka_interval, next_time))
    ka_thread.start()
    
    # Allow closing of window to close everything.
    def closewrapper():
        ka_interval.set(-1)
        app.destroy()
        s.shutdown(socket.SHUT_RDWR)
    app.protocol("WM_DELETE_WINDOW", closewrapper)
    app.insert(">>>> Waiting for server to provide peer.")
    
    # Server response format:
    # {requester ip}\n{requester port}\n{other ip}\n{other port}\n{random key}
    while True:
        data, address = s.recvfrom(65507) # Always receive max UDP packet size.
        if address == server_address:
            break
    
    data = data.split("\n")
    my_addr = (data[0], int(data[1]))
    other_addr = (data[2], int(data[3]))
    punch_key = data[4] # Assume punch_key is length 8. Not checked.
    
    app.insert(">>>> Connecting to {}...".format(other_addr))
    app.insert('>>>> Punch key : "{}"...'.format(punch_key))
    logger.info('Recevied from server:\n{}\n{}\n"{}"'.format(my_addr, other_addr, punch_key))
    
    # Handshaking. Can be made more robust, but for the sake of simplicity:
    # Assume that all clients follow protocol. This means that max difference in
    # state between 2 clients is 1 (i.e. No state 0 and state 2.)
    # Also, clients only send actual data when state is 2.
    state = 0
    hs_payload = punch_key + STATEMAP[state]
    ka_box.set((hs_payload,other_addr))
    ka_interval.set(1)
    while state<2:
        data, address = s.recvfrom(65507)
        if address != other_addr or data[0:8] != punch_key:
            continue
        # use -1 for invalid states (errors). Accept but won't do anything.
        givenstate = STATEMAP.get(data[8:16], -1) + 1
        if givenstate > state:
            prev_state = state
            state = givenstate if givenstate<=2 else 2 # Max state is 2.
            hs_payload = "{}{}".format(punch_key, STATEMAP[state])
            ka_box.set((hs_payload,other_addr))
            logger.info("Changed from state {} to {}".format(prev_state, state))
    ka_interval.set(10)
    
    app.insert(">>>> Connected.")
    
    # There may be data sent in the previous message if state from other client is 2.
    # To guard against this, simply try to process data first.
    # Process and Receive data.
    while ka_interval.get() > 0:
        # process data here
        data, address = s.recvfrom(65507)
        if address != other_addr or data[0:8] != punch_key:
            continue
    
    # End
    ka_interval.set(-1)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ip', type=str, default="3.0.0.2", help='Server ip')
    parser.add_argument('-p', '--port', type=int, default=80, help='Server port')
    parser.add_argument('room', type=int, default=0, help='Room ID')
    args = parser.parse_args()
    server_address = (args.ip, args.port)
    
    main(args.room, server_address)