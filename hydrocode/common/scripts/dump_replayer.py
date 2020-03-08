#!/usr/bin/env python3

# Script for replaying raw hydrophones data dumps. Read Hydrophones Code wiki entry for more details.

import socket, time, sys

PKT_LEN = 63 # number of samples from each channel in a hydrophones packet
PKT_HEADER_SIZE = 7 # size of packet header (Bytes)
NUM_CHS = 4 # number of channels
SAMPLE_RATE = 153061 # self explanatory huh?
ADDR = "127.0.0.1" # local host because we are sending the data to the same machine
PINGER_PORT = 49152 # pingerd listens on this port
COMMS_PORT = 49153 # commsd listens on this port

port = PINGER_PORT

# check whether dump filename was specified
try:
	dump_filename = sys.argv[1]
except IndexError:
	print("Dump filename not specified")
	raise

# choose where to send packets
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

# get binary file size
def getSize(file):
	file.seek(0, 2)
	size = file.tell()
	return size

 # load binary file specified from terminal
dump = open(dump_filename, "rb")

# initialize UDP networking
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

pkt_size = NUM_CHS * PKT_LEN * 2 + PKT_HEADER_SIZE

print("Replaying " + dump_filename + "...")

# send packets
for pkt_num in range(int(getSize(dump) / pkt_size)):
	dump.seek(pkt_num * pkt_size)
	sock.sendto(dump.read(pkt_size), (ADDR, port))

	# wait for the amount of time the hydrophones board would take to send another packet
	time.sleep(PKT_LEN / SAMPLE_RATE)