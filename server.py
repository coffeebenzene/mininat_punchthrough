import socket, random, time

SERVER_IP = "3.0.0.2"
PORT = 1024

information = {} #array of addresses

def main():
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) #declare is internet and UDP connection
    sock.bind((SERVER_IP,PORT))
    while True:
        room_id,address = sock.recvfrom(1024) #6
        # ip_add = address[0]
        # port = address[1]
        if room_id not in information:
            d[room_id] = address
            timeout = time.time() + 300 #start the timeout

        #the second time a room ID is received aka there's a request from h2
        else:
            if time.time() > timeout:
                information.clear() #delete the room and try again
            else:
                #combine source from h1 and h2
                #generate the key
                key = random.randint(0,999999)
                key = "%06d" %(key)

                #concanate the two address together to send to the client
                data_for_second_host = address[0] + '\n' + address[1] + '\n' + information[room_id][0] + '\n' + information[room_id][1] + str(key)
                data_for_first_host = information[room_id][0] + '\n' + information[room_id][1] + address[0] + '\n' + address[1] + '\n' + str(key)

                #send the information to each host

                sock.sendto(data_for_first_host,information[room_id])

                sock.sendto(data_for_second_host,address)





