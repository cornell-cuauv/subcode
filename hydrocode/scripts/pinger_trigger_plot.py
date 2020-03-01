#!/usr/bin/env python3

import socket, struct, numpy, math
import matplotlib.pyplot as plt
from scipy import interpolate

LEN = 20
PKT_LEN = 64
ADDR = "127.0.0.1"
PORT = 49155

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ADDR, PORT))

fig = plt.figure(figsize = (7, 7))

x = numpy.arange(-LEN + 1, 1)
smooth_x = numpy.linspace(-LEN + 1, 0, num = "1000")
smooth_y = smooth_x

plt.subplot(2, 1, 1)
plt.title("Amplitude")
plt.xticks(numpy.arange(-LEN + 1, 1, LEN // 10))
ax1 = plt.gca()
ax1.set_xlim(-LEN + 1, 0)
(ampl0_line, ampl1_line, ampl2_line, ampl3_line) = ax1.plot(smooth_x, smooth_y, 'r-', smooth_x, smooth_y, 'g-', smooth_x, smooth_y, 'b-', smooth_x, smooth_y, 'm-', linewidth = 0.5)

plt.subplot(2, 1, 2)
plt.title("Phase")
plt.xticks(numpy.arange(-LEN + 1, 1, LEN // 10))
ax2 = plt.gca()
ax2.set_xlim(-LEN + 1, 0)
ax2.set_ylim(-2 * math.pi, 2 * math.pi)
(ph0_line, ph1_line, ph2_line, ph3_line) = ax2.plot(smooth_x, smooth_y, 'r-', smooth_x, smooth_y, 'g-', smooth_x, smooth_y, 'b-', smooth_x, smooth_y, 'm-', linewidth = 0.5)

decode_str = str(2 * LEN) + 'f'

print("Listening for plots...")

while 1:
	real_values = list()
	imag_values = list()
	smooth_amplitudes = list()
	smooth_phases = list()

	for signal_index in range(4):
		data = bytes()

		for pkt_num in range(int(math.ceil(LEN / PKT_LEN))):
			(data_pkt, recv_addr) = sock.recvfrom(2 * PKT_LEN * 4)
			data += data_pkt

		interleaved_values = numpy.asarray(struct.unpack(decode_str, data))
		real_values.append(interleaved_values[0::2])
		imag_values.append(interleaved_values[1::2])

	print("Received pinger trigger plot")

	for signal_index in range(4):
		real_function = interpolate.splrep(x, real_values[signal_index])
		smooth_real_value = interpolate.splev(smooth_x, real_function)

		imag_function = interpolate.splrep(x, imag_values[signal_index])
		smooth_imag_value = interpolate.splev(smooth_x, imag_function)

		smooth_amplitudes.append(numpy.abs(smooth_real_value + 1j * smooth_imag_value));
		smooth_phases.append(numpy.angle(smooth_real_value + 1j * smooth_imag_value));

	ampl0_line.set_ydata(smooth_amplitudes[0])
	ampl1_line.set_ydata(smooth_amplitudes[1])
	ampl2_line.set_ydata(smooth_amplitudes[2])
	ampl3_line.set_ydata(smooth_amplitudes[3])

	ph0_line.set_ydata(smooth_phases[0])
	ph1_line.set_ydata(smooth_phases[1])
	ph2_line.set_ydata(smooth_phases[2])
	ph3_line.set_ydata(smooth_phases[3])

	max_ampl = max([smooth_amplitudes[0].max(), smooth_amplitudes[1].max(), smooth_amplitudes[2].max(), smooth_amplitudes[3].max()])
	ax1.set_ylim(-0.1 * max_ampl, 1.1 * max_ampl)

	plt.draw()
	plt.pause(0.1)