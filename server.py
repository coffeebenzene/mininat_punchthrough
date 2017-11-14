import socket, random

SERVER_IP = "3.0.0.1"
PORT = 1024

information = [] #array of addresses
room_id = []
def main():
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) #declare is internet and UDP connection
    sock.bind((SERVER_IP,PORT))
    while True:
        data, address = sock.recvfrom(1024)
        ip_add = address[0]
        port = address[1]
        if len(information) != 2:
            information.append(address)
            room_id.append(data)
        #the second time a room ID is received
        if len(room_id) == 2:
            #combine source from h1 and h2
            #generate the key
            key = random.randint(1000,9999) #4 digit key

        '''
        a chunk that timesout if there are no more request 
        '''

        #send the information to each host
        payload_forh1 = str(address[1]) #pseudo code to convert addresses into messages that can be sent
        sock.sendto(payload_forh1,(address[0][0],address[0][1]))
        payload_forh2 = str(address[0])
        sock.sendto(payload_forh2, (address[1][0], address[1][1]))





