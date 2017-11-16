def fragmentation(packet):
    fragmented_array = []
    # max_byte = 65507
    size_to_break_down = 50 * 1000 #50kB
    data_length = len(packet)
    # print data_length
    times_to_break_down = data_length / size_to_break_down
    remainder = data_length % size_to_break_down
    for i in range(times_to_break_down):
        fragmented_array.append(packet[size_to_break_down*i:size_to_break_down*(i+1)])
    #insert the remaining trail
    fragmented_array.append(packet[(size_to_break_down*times_to_break_down):])
    return fragmented_array

print fragmentation("A" * 65507 * 2)
print("A" * 65507 * 2)
print("%08d" %(0))