#!/usr/bin/env python3

import socket, struct, numpy, math
import matplotlib.pyplot as plt
from scipy import interpolate

LEN = 70
PKT_LEN = 128
ADDR = "127.0.0.1"
PORT = 49156

BIT_DEPTH = 16384

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ADDR, PORT))

fig = plt.figure(figsize = (7, 7))

x = numpy.arange(0, LEN)
y = x
smooth_x = numpy.linspace(0, LEN - 1, num = "1000")
smooth_y = smooth_x

plt.subplot(2, 1, 1)
plt.title("Signal")
plt.xticks(numpy.arange(0, LEN, LEN // 10))
ax1 = plt.gca()
ax1.set_xlim(0, LEN - 1)
ax1.set_ylim(0, BIT_DEPTH // 4)
(sig0_line, sig1_line, sig2_line, sig3_line) = ax1.plot(smooth_x, smooth_y, 'r-', smooth_x, smooth_y, 'g-', smooth_x, smooth_y, 'b-', linewidth = 0.5)

plt.subplot(2, 1, 2)
plt.title("Gain")
plt.xticks(numpy.arange(0, LEN, LEN // 10))
ax2 = plt.gca()
ax2.set_xlim(0, LEN - 1)
ax2.set_ylim(0, 200)
(gain_line, ) = ax2.plot(x, y, linewidth = 0.5)

decode_str = str(LEN) + 'f'

print("Listening for plots...")

while 1:
	values = list()
	smooth_values = list()

	for signal_index in range(5):
		data = bytes()

		for pkt_num in range(int(math.ceil(LEN / PKT_LEN))):
			(data_pkt, recv_addr) = sock.recvfrom(PKT_LEN * 4)
			data += data_pkt

		values = numpy.asarray(struct.unpack(decode_str, data))

	print("Received comms raw plot")

	for signal_index in range(4):
		function = interpolate.splrep(x, values[signal_index])
		smooth_values.append(interpolate.splev(smooth_x, function))

	sig0_line.set_ydata(numpy.abs(smooth_values[0])
	sig1_line.set_ydata(numpy.abs(smooth_values[1])
	sig2_line.set_ydata(numpy.abs(smooth_values[2])
	sig3_line.set_ydata(numpy.abs(smooth_values[3])

	gain_line.set_ydata(values[4])

	plt.draw()
	plt.pause(0.1)