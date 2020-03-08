#!/usr/bin/env python3

# Script for dumping raw hydrophones data to a mat file. Read Hydrophones Code wiki entry for more details.

import socket, time

PKT_LEN = 63 # number of samples from each channel in a hydrophones packet
PKT_HEADER_SIZE = 7 # size of packet header (Bytes)
NUM_CHS = 4 # number of channels
SAMPLE_RATE = 153061 # self explanatory huh?
ADDR = "" # receive from any network interface
PINGER_PORT = 49152 # hydrophones board sends pinger samples to this port
COMMS_PORT = 49153 # hydrophones board sends comms samples to this port

port = PINGER_PORT

# choose where to listen
while True:
	try:
		mode = input("Enter 'pinger' or 'comms': ")
		if mode == "pinger":
			port = PINGER_PORT
			break
		elif mode == "comms":
			port = COMMS_PORT
			break
		else:
			raise ValueError("Specified mode does not exist")
	except ValueError:
		print("Invalid input")

# initialize UDP networking
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ADDR, port))

pkt_num = 0
start_time = time.time()
last_print_time = start_time

print("Listening for packets...")

with open("dump.dat", "wb") as dump:
	try:
		while True:
			# receive a packet (blocking)
			(data, recv_addr) = sock.recvfrom(NUM_CHS * PKT_LEN * 2 + PKT_HEADER_SIZE)

			pkt_num += 1

			# print number of packets per second approximately every second
			if pkt_num % int(SAMPLE_RATE / PKT_LEN) == 0:
				curr_time = time.time()
				print('\n' + str(int(SAMPLE_RATE / PKT_LEN / (curr_time - last_print_time))) + " packets per second")
				last_print_time = curr_time

			# write packet
			dump.write(data)

	# end dump upon keyboard interrupt
	except KeyboardInterrupt:
		print("\ndumped " + str(pkt_num) + " packets in " + "{:.2f} seconds".format(time.time() - start_time))