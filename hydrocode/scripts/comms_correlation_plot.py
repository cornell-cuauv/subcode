#!/usr/bin/env python3

import socket, struct, numpy, math
import matplotlib.pyplot as plt
from scipy import interpolate

LEN = 1 * 10**3
PKT_LEN = 128
ADDR = "127.0.0.1"
PORT = 49157

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ADDR, PORT))

fig = plt.figure(figsize = (7, 7))

x = numpy.arange(-LEN + 1, 1)
smooth_x = numpy.linspace(-LEN + 1, 0, num = "1000")
smooth_y = smooth_x

plt.subplot(2, 1, 1)
plt.title("Correlation Input")
plt.xticks(numpy.arange(-LEN + 1, 1, LEN // 10))
ax1 = plt.gca()
ax1.set_xlim(-LEN + 1, 0)
(in_line, ) = ax1.plot(smooth_x, smooth_y, 'k-', linewidth = 0.5)

plt.subplot(2, 1, 2)
plt.title("Correlation Results")
plt.xticks(numpy.arange(-LEN + 1, 1, LEN // 10))
ax2 = plt.gca()
ax2.set_xlim(-LEN + 1, 0)
(sig_out_line, orth_out_line, dyn_thresh_line) = ax2.plot(smooth_x, smooth_y, 'g-', smooth_x, smooth_y, 'r-', smooth_x, smooth_y, 'b-', linewidth = 0.5)

decode_str = str(LEN) + 'f'

print("Listening for plots...")

while 1:
	values = list()
	smooth_values = list()

	for signal_index in range(4):
		data = bytes()

		for pkt_num in range(int(math.ceil(LEN / PKT_LEN))):
			(data_pkt, recv_addr) = sock.recvfrom(PKT_LEN * 4)
			data += data_pkt

		values.append(numpy.asarray(struct.unpack(decode_str, data)))

	print("Received comms corr plot")

	for signal_index in range(4):
		function = interpolate.splrep(x, values[signal_index])
		smooth_values.append(interpolate.splev(smooth_x, function))

	in_line.set_ydata(smooth_values[0])
	sig_out_line.set_ydata(smooth_values[1])
	orth_out_line.set_ydata(smooth_values[2])
	dyn_thresh_line.set_ydata(smooth_values[3])

	ax1.set_ylim(in_line.min(), in_line.max())
	ax2.set_ylim(min([smooth_values[1].min(), smooth_values[2].min(), smooth_values[3].min()]), max([smooth_values[1].max(), smooth_values[2].max(), smooth_values[3].max()]))

	plt.draw()
	plt.pause(0.1)