import argparse
import collections
import socket
import threading
import time
import logging

import Tkinter as tkr
import ttk
import ScrolledText

logging.basicConfig()
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
        self.textarea_lock = threading.Lock()

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
        with self.textarea_lock:
            self.textarea.configure(state=tkr.NORMAL)
            self.textarea.insert(tkr.END, text)
            self.textarea.insert(tkr.END, "\n")
            self.textarea.configure(state=tkr.DISABLED)

    def allow_sending(self, sendqueue, send_semaphore):
        self.sendqueue = sendqueue
        self.send_semaphore = send_semaphore
        self.sendbtn["state"] = tkr.NORMAL

    def send(self, event=None):
        usr_input = self.input_field.get()
        usr_inp_list = usr_input.split(" ")
        if usr_inp_list[0] == ">sendfile":
            msg_type = "FILE"
            try:
                with open(usr_inp_list[1]) as f:
                    l = usr_inp_list[1]
                    l += "|"
                    l += f.read()
            except IOError:
                self.insert_text("Error: File could not be read")
        else:
            msg_type = "MSG "
            l = usr_input

        self.sendqueue.append((l, msg_type, "FULL", "00000000"))
        self.input_val.set("")
        self.send_semaphore.release()



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


def punchthrough_receive(app, room_id, server_address):
    # UDP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1.0) # Make thread interruptable

    # Setup keepalive variables
    ka_box = AtomicVariable((room_id, server_address))
    ka_interval = AtomicVariable(10)
    next_time = AtomicVariable(time.time())
    # punchthrough_receive() exclusively uses keepalive thread for sending data via ka_box.
    # Initially request to server for connection.
    threading.Thread(target=keepalive, args=(s, ka_box, ka_interval, next_time)).start()

    # Allow closing of window to close everything.
    def closewrapper():
        ka_interval.set(-1)
        next_time.set(time.time())
        app.master.destroy()
        s.close()
    app.master.protocol("WM_DELETE_WINDOW", closewrapper)
    app.insert_text(">>>> Waiting for server to provide peer.")

    # Server response format:
    # {requester ip}\n{requester port}\n{other ip}\n{other port}\n{random key}
    while True:
        try:
            data, address = s.recvfrom(65507) # Always receive max UDP packet size.
        except socket.timeout:
            continue
        if address == server_address:
            break

    data = data.split("\n")
    my_addr = (data[0], int(data[1]))
    other_addr = (data[2], int(data[3]))
    punch_key = data[4] # Assume punch_key is length 8. Not checked.

    app.insert_text(">>>> Connecting to {}...".format(other_addr))
    app.insert_text('>>>> Punch key : "{}"...'.format(punch_key))
    logger.info('Recevied from server:\n{}\n{}\n"{}"'.format(my_addr, other_addr, punch_key))

    # Handshaking. Can be made more robust, but for the sake of simplicity:
    # Assume that all clients follow protocol. This means that max difference in
    # state between 2 clients is 1 (i.e. No state 0 and state 2.)
    # Also, clients only send actual data when state is 2.
    state = 0
    hs_payload = punch_key + STATEMAP[state]
    ka_box.set((hs_payload,other_addr))
    ka_interval.set(1)
    next_time.set(time.time())
    while state<2:
        try:
            data, address = s.recvfrom(65507)
        except socket.timeout:
            if ka_interval.get() < 0: # Allow exiting.
                raise
            continue
        if address != other_addr or data[0:8] != punch_key:
            continue
        # use -1 for invalid states (errors). Accept but won't do anything.
        givenstate = STATEMAP.get(data[8:16], -1) + 1
        if givenstate > state:
            prev_state = state
            state = givenstate if givenstate<=2 else 2 # Max state is 2.
            hs_payload = punch_key + STATEMAP[state]
            ka_box.set((hs_payload,other_addr))
            logger.info("Changed from state {} to {}".format(prev_state, state))
    ka_interval.set(10)

    app.insert_text(">>>> Connected.")

    # Allow sending on GUI and initialize sender/receiver variables
    sendqueue = collections.deque()
    send_semaphore = threading.Semaphore(0)
    app.allow_sending(sendqueue, send_semaphore)
    other_acknum = AtomicVariable(1)
    acknum = AtomicVariable(99999998) # Should start from 1. Start at 99999997+1 to prove that handles overflow.
    sender_params = {"sendqueue" : sendqueue,
                     "send_semaphore" : send_semaphore,
                     "other_acknum" : other_acknum,
                     "other_addr" : other_addr,
                     "s" : s,
                     "ka_interval" : ka_interval,
                     "next_ka_time" : next_time,
                     "acknum" : acknum,
                     "first_header" : punch_key + STATEMAP[state],
                     "app" : app,
                    }
    threading.Thread(target=sender, args=(sender_params,)).start()

    # There may be data sent in the previous message if state from other client is 2.
    # To guard against this, simply try to process data first.
    # Requires inner loop on Receive data part. (Alternative is duplicate process data part before loop.)
    # keepalive() is used for sending ACKs.
    # ASSUMES DATAGRAMS ARE RECEIVED IN ORDER.
    def recv_file(recv_msg):
        msg_list = recv_msg.split("|")
        filename = msg_list[0]
        msg_list.pop(0)
        file_data = "|".join(msg_list)
        with open(msg_list[0], 'w+') as f:
            f.write(file_data)
        app.insert_text("File saved: {}".format(filename))

    msg_action = {"MSG " : lambda recv_msg : app.insert_text("Peer: {}".format(recv_msg)),
                  "FILE" : lambda recv_msg : recv_file(recv_msg), # ask to receive file.
                 }
    prev_fragnum = None
    fraglist = []
    while ka_interval.get() > 0:
        # process data
        if len(data) >= 48:
            recv_seqnum = int(data[16:24])
            recv_acknum = int(data[24:32])
            msg_type = data[32:36]
            frag_ident = data[36:40]
            fragnum = int(data[40:48])
            recv_msg = data[48:]

            if msg_type != "KA  " and recv_seqnum == acknum.get(): # Process non-keepalive messages
                if frag_ident=="FRAG": # Fragemented message
                    if not ( prev_fragnum == fragnum or prev_fragnum == None ):
                        fraglist = []
                        logger.error("FRAGMENT NUMBER CHANGED. Previous fragment dropped.")
                    # Add fragment
                    fraglist.append(recv_msg)
                    prev_fragnum = fragnum
                    # last fragment
                    if fragnum == recv_seqnum:
                        msg_action[msg_type]("".join(fraglist))
                        prev_fragnum = None
                        fraglist = []
                else: # Full message
                    msg_action[msg_type](recv_msg)

                # Set ACK response
                acknum.set((recv_seqnum + 1) % 100000000)
                ka_payload = [punch_key, STATEMAP[state],
                              "00000000", "{:08}".format(acknum.get()),
                              "KA  ", "FULL", "00000000"]
                ka_payload = "".join(ka_payload)
                ka_box.set((ka_payload,other_addr))
                next_time.set(time.time())

            # Update other_acknum for sender (Any message, including keepalive, can unpdate ACKs)
            other_acknum.set(recv_acknum)

        # Receive data (ignore non-NAT punchthrough datagrams)
        while ka_interval.get() > 0:
            try:
                data, address = s.recvfrom(65507)
            except socket.timeout:
                continue
            if address == other_addr and data[0:8] == punch_key:
                break


def sender(sender_params):
    s = sender_params["s"]
    other_addr = sender_params["other_addr"]
    other_acknum = sender_params["other_acknum"]
    sendqueue = sender_params["sendqueue"]
    send_semaphore = sender_params["send_semaphore"]
    ka_interval = sender_params["ka_interval"]
    next_ka_time = sender_params["next_ka_time"]
    acknum = sender_params["acknum"]
    first_header = sender_params["first_header"]
    app = sender_params["app"]

    windowsize = 1
    window = collections.deque(maxlen=windowsize) # (fullmsg, seqnum) waiting for ack. fullmsg is header+message.
    timeout = 3 # timeout for window to resend in seconds
    next_timeout = time.time()
    seqnum = 99999997 # Should start from 0. Start at 99999997 to prove that handles overflow.

    while ka_interval.get() > 0:
        # Remove ACK'd messages.
        acked_seqnum = (other_acknum.get() - 1) % 100000000
        popnum = 0
        for i, (fullmsg, msg_seqnum) in enumerate(window, 1):
            if msg_seqnum == acked_seqnum:
                popnum = i
                break
        for i in range(popnum):
            window.popleft()

        # window timed out, resend
        if time.time() > next_timeout:
            for fullmsg, msg_seqnum in window:
                s.sendto(fullmsg, other_addr)
            next_timeout = time.time() + timeout

        # window is not full and there are messages, send more.
        if len(window) < windowsize and send_semaphore.acquire(False):
            msg, msg_type, frag_ident, fragnum = sendqueue.popleft()

            # Message exceeds max payload size 50000B, fragment and requeue
            # (max payload size must be less than max_UDP_payload - header_size, 50K is a nice round number.)
            if frag_ident=="FULL" and len(msg) > 50000:
                num_frags = ((len(msg)-1)//50000)+1 # ceil division
                last_seqnum = (seqnum + num_frags) % 100000000 # Account for overflow
                # insert reverse order so that popleft will be in order.
                for i in range(numfrags, 0, -1):
                    msgfrag = msg[i,i+50000]
                    sendqueue.appendleft((msgfrag, msg_type, "FRAG", "{:08}".format(last_seqnum)))
                    send_semaphore.release()
            else: # Normal message to send.
                seqnum = (seqnum + 1) % 100000000 # Account for overflow
                fullmsg = [first_header,
                           "{:08}".format(seqnum), "{:08}".format(acknum.get()),
                           msg_type, frag_ident, fragnum,
                           msg]
                fullmsg = "".join(fullmsg)
                s.sendto(fullmsg, other_addr)
                window.append((fullmsg, seqnum))
                next_ka_time.set(time.time() + ka_interval.get())
                next_timeout = time.time() + timeout
                if msg_type == "MSG ":
                    app.insert_text("Me: {}".format(msg))
        else: # nothing to send, sleep (poll).
            time.sleep(0.1)



# Main GUI thread.
def main(room_id=0, server_address=("3.0.0.2",80)):
    if not (0 <= room_id <= 999999):
        raise ValueError("Room ID must be a 6 digit number (0-999999).")
    room_id = "{:06}".format(room_id)

    app = Application(master=tkr.Tk())
    threading.Thread(target=punchthrough_receive, args=(app, room_id, server_address)).start()

    app.mainloop()



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ip', type=str, default="3.0.0.2", help='Server ip')
    parser.add_argument('-p', '--port', type=int, default=80, help='Server port')
    parser.add_argument('room', type=int, default=0, help='Room ID')
    args = parser.parse_args()
    server_address = (args.ip, args.port)

    main(args.room, server_address)