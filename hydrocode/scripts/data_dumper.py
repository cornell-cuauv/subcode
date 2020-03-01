#!/usr/bin/env python3

# Script for dumping raw hydrophones data to a mat file. Read Hydrophones Code wiki entry for more details.

import socket, time

PKT_LEN = 31 # number of samples from each channel in a hydrophones packet
PKT_HEADER_SIZE = 10 # size of packet header (Bytes)
NUM_CHS = 8 # number of channels
ADDR = "" # receive from any network interface
PORT = 49152 # hydrophones board sends packets to this port

# initialize UDP networking
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ADDR, PORT))

pkt_num = 0
start_time = time.time()
last_print_time = start_time

# open binary file
dump = open("dump.dat", "wb")

print("Listening for packets...")

try:
	while 1:
		# receive a packet (blocking)
		(data, recv_addr) = sock.recvfrom(NUM_CHS * PKT_LEN * 2 + PKT_HEADER_SIZE)

		pkt_num += 1

		# print number of packets per second approximately every second
		if pkt_num % 4937 == 0:
			print('\n' + str(4937 // (time.time() - last_print_time)) + " packets per second")
			last_print_time = time.time()

		# write packet
		dump.write(data)

# end dump upon keyboard interrupt
except KeyboardInterrupt:
	print("\ndumped " + str(pkt_num) + " packets in " + "{:.2f} seconds".format(time.time() - start_time))