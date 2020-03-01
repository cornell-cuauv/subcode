#!/usr/bin/env python3

# Script for replaying raw hydrophones data dumps. Read Hydrophones Code wiki entry for more details.

import socket, time, sys

PKT_LEN = 31 # number of samples from each channel in a hydrophones packet
PKT_HEADER_SIZE = 10 # size of packet header (Bytes)
NUM_CHS = 8 # number of channels
SAMPLE_RATE = 153061 # self explanatory huh?
ADDR = "127.0.0.1" # local host because we are sending the data to the same machine
PORT = 49152 # hydromathd listens on this port

# get binary file size
def getSize(file):
	file.seek(0, 2)
	size = file.tell()
	return size

 # load binary file specified from terminal
dump = open(sys.argv[1], "rb")

# initialize UDP networking
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

pkt_size = NUM_CHS * PKT_LEN * 2 + PKT_HEADER_SIZE

print("Replaying " + sys.argv[1] + "...")

# send packets
for pkt_num in range(int(getSize(dump) / pkt_size)):
	dump.seek(pkt_num * pkt_size)
	sock.sendto(dump.read(pkt_size), (ADDR, PORT))

	# wait for the amount of time the hydrophones board would take to send another packet
	time.sleep(PKT_LEN / SAMPLE_RATE)