#!/usr/bin/env python3

import socket, struct, numpy, math
import matplotlib.pyplot as plt
from scipy import interpolate

LEN = 21 * 10**3
PKT_LEN = 128
ADDR = "127.0.0.1"
PORT = 49154

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ADDR, PORT))

fig = plt.figure(figsize = (7, 7))

x = numpy.arange(0, LEN)
y = x
smooth_x = numpy.linspace(0, LEN - 1, num = "1000")
smooth_y = smooth_x

plt.subplot(2, 1, 1)
plt.title("Combined Amplitude")
plt.xticks(numpy.arange(0, LEN, int(LEN / 10)))
ax1 = plt.gca()
ax1.set_xlim(0, LEN - 1)
(ampl_line, ) = ax1.plot(smooth_x, smooth_y, 'k-', linewidth = 0.5)
trigger_cursor_ampl = ax1.axvline(x = 0, ymax = 0.09, color = "blue", linewidth = 0.5)

plt.subplot(2, 1, 2)
plt.title("Sense Ratio")
plt.xticks(numpy.arange(0, LEN, int(LEN / 10)))
ax2 = plt.gca()
ax2.set_xlim(0, LEN - 1)
(ratio_line, ) = ax2.plot(x, y, 'k-', linewidth = 0.5)
trigger_cursor_ratio = ax2.axvline(x = 0, ymax = 0.09, color = "blue", linewidth = 0.5)

decode_str = str(LEN) + 'f'

print("Listening for plots...")

while True:
	values = list()

	for signal_index in range(2):
		data = bytes()

		for pkt_num in range(int(math.ceil(LEN / PKT_LEN))):
			(data_pkt, recv_addr) = sock.recvfrom(PKT_LEN * 4)
			data += data_pkt

		values.append(numpy.asarray(struct.unpack(decode_str, data)))

	(data, recv_addr) = sock.recvfrom(4)
	trigger_n = int(struct.unpack('f', data)[0])

	print("Received pinger sense plot")

	function = interpolate.splrep(x, values[0])
	smooth_amplitude = interpolate.splev(smooth_x, function)

	ampl_line.set_ydata(smooth_amplitude)
	ratio_line.set_ydata(values[1])
	trigger_cursor_ampl.set_xdata(trigger_n)
	trigger_cursor_ratio.set_xdata(trigger_n)

	ax1.set_ylim(-0.1 * smooth_amplitude.max(), 1.1 * smooth_amplitude.max())
	ax2.set_ylim(-0.1 * values[1].max(), 1.1 * values[1].max())

	plt.draw()
	plt.pause(1.5)