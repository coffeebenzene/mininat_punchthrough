import socket, random, time
import argparse



information = {} #array of addresses

def main(port):
    SERVER_IP = "3.0.0.2"
    PORT = port
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) #declare is internet and UDP connection
    sock.bind((SERVER_IP,PORT))
    print "entering while loop"
    while True:
        room_id,address = sock.recvfrom(1024) #6
        print "I have received a connection"
        # ip_add = address[0]
        # port = address[1]
        if room_id not in information:
            print "Registering first host"
            information[room_id] = address
            timeout = time.time() + 300 #start the timeout
            print "setted timeout"

        #the second time a room ID is received aka there's a request from h2
        else:
            if time.time() > timeout:
                print "timedout occured."
                information.clear() #delete the room and try again
            else:
                #combine source from h1 and h2
                #generate the key
                print "timeedout did not occur & second host has connected"
                key = random.randint(0,99999999)
                key = "%08d" %(key)
                print "key: " + str(key)
                #concanate the two address together to send to the client
                data_for_second_host = str(address[0]) + '\n' + str(address[1]) + '\n' + str(information[room_id][0]) + '\n' + str(information[room_id][1]) + '\n' + str(key)
                data_for_first_host = str(information[room_id][0]) + '\n' + str(information[room_id][1]) + '\n' + str(address[0]) + '\n' + str(address[1]) + '\n' + str(key)
                print "for 1st host: \n"  +data_for_first_host
                print "for 2nd host: \n" + data_for_second_host
                #send the information to each host

                sock.sendto(data_for_first_host,information[room_id])
                print "sent to 1st host"
                sock.sendto(data_for_second_host,address)
                print "sent to 2nd host"

                print "Clearing the room id information"
                information.clear()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default="1025", help='Set Server Port')
    args = parser.parse_args()
    main(args.port)
