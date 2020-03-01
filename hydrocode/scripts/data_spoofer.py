#!/usr/bin/env python3

# Script for simulating one ping worth of data. Read Hydrophones Code wiki entry for more details.

import numpy

HDG = 45 # ping heading (degrees)
ELEV = 10 # ping elevation (degrees)
SIGNAL_AMPL = numpy.array([0.99, 0.99, 0.99, 0.99]).transpose()
NOISE_AMPL = 0.01 # amplitude of sine noise at ping frequency (max 1)
FREQ = 25000 # ping frequency (Hz)
IDLE_TIME = 3.996 # padding before ping (seconds)
PING_TIME = 0.004 # ping duration (seconds)
POST_TIME = 1 # padding after ping (seconds)

PKT_LEN = 31 # number of samples from each channel in a hydrophones packet
BIT_DEPTH = 16384 # number of quantization levels
SAMPLE_RATE = 153061 # self explanatory huh?
NIPPLE_DIST = 0.0178 # distance between the teats (meters)
SOUND_SPEED = 1481 # speed of sound in fresh water at 20 degrees Celsius (m/s)

n_idle = int(IDLE_TIME * SAMPLE_RATE)
n_ping = int(PING_TIME * SAMPLE_RATE)
n_post = int(POST_TIME * SAMPLE_RATE)
n_total = n_idle + n_ping + n_post
n_start = \
numpy.array([
	n_idle, \
	n_idle - NIPPLE_DIST * SAMPLE_RATE / SOUND_SPEED * numpy.sin(numpy.radians(HDG)) * numpy.cos(numpy.radians(ELEV)), \
	n_idle + NIPPLE_DIST * SAMPLE_RATE / SOUND_SPEED * numpy.cos(numpy.radians(HDG)) * numpy.cos(numpy.radians(ELEV)), \
	n_idle - NIPPLE_DIST * SAMPLE_RATE / SOUND_SPEED * numpy.sin(numpy.radians(ELEV)) \
], dtype = numpy.uint)

num_ch = len(SIGNAL_AMPL)
omega_hat = 2 * numpy.pi * FREQ / SAMPLE_RATE

dump = open("spoofed_dump.dat", "wb")

print("Generating data...")

for pkt_num in range(int(n_total / PKT_LEN)):
	n_offset = pkt_num * PKT_LEN
	n = numpy.arange(n_offset, n_offset + PKT_LEN)

	noise = (BIT_DEPTH - 1) / 2 * NOISE_AMPL * numpy.sin(omega_hat * n)

	print(n_start.shape)

	signal = (n_start >= n > n_start + n_ping) * ((BIT_DEPTH - 1) / 2 * SIGNAL_AMPL * numpy.sin(omega_hat * (n - n_start))) + noise

	pkt_data = numpy.zeros[num_ch * PKT_LEN]
	for ch_num in range(num_ch):
		pkt_data[ch_num::num_ch] = signal[ch_num]

	high_sample = numpy.max(pkt_data)

	# write packet header
	dump.write(numpy.array([pkt_num], dtype = "<u4").tobytes())
	dump.write(numpy.array([0], dtype = "<u1").tobytes())
	dump.write(numpy.array([high_sample], dtype = "<u2").tobytes())

	# write packet data
	dump.write(pkt_data.tobytes())