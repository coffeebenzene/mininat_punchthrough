import socket, random, time
import argparse

information = {} #array of addresses
timeOuts = {}
socketTimeOut = 30
clientConnectionTimeOut = 300

def main(port):
    SERVER_IP = "3.0.0.2"
    PORT = port
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) #declare is internet and UDP connection
    sock.bind((SERVER_IP,PORT))
    sock.settimeout(socketTimeOut)

    print "entering while loop"
    while True:
        """
        This code operates under the assumption that clients will continually send connection request messages
        """
        #This creates a dictionary of all connections which have timed out
        timedOutConnections = {k:v for (k,v) in timeOuts.items() if v < time.time()}
        print "Timed out connections: {0}".format(timedOutConnections)
        for roomID, timeOut in timedOutConnections.iteritems():
            print "Timed out: Kicking roomID: {0}".format(roomID)
            timeOuts.pop(roomID) #delete the room and try again
            information.pop(roomID)	
        
        try:
            room_id,address = sock.recvfrom(1024) #6
        except socket.timeout:
            print("Skip")
            continue
		
	     print "I have received a connection"
        if information[room_id][0] == address[0]:
            print "Same idiot spamming us requests, ignore him"
            continue 
        
        elif room_id not in information:
            print "Registering first host"
            information[room_id] = address
            timeout = time.time() + clientConnectionTimeOut #start the timeout
            timeOuts[room_id]  = timeout
            print "setted timeout: {0}".format(timeout)

        #Check if the message was sent by the same guy again 

        else:
            #Check if the time has yet to expire
            if time.time() > timeOuts[room_id]:
                print "timedout occured." # Let the code segment before the try statement do the popping
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
