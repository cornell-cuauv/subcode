#!/usr/bin/env python3

import sys, numpy

PKT_LEN = 63
NUM_CHS = 4
BIT_DEPTH = 16384
SAMPLE_RATE = 153061
NIPPLE_DIST = 0.0178
SOUND_SPEED = 1481
MAX_DUR = 10**7

max_travel_time = NIPPLE_DIST / SOUND_SPEED * SAMPLE_RATE

try:
	input_filename = sys.argv[1]
except IndexError:
	print("Input filename not specified")
	raise

while True:
	try:
		hdg_deg = float(input("Enter heading (deg) in the interval [0, 360): "))
		if 0 <= hdg_deg < 360:
			hdg = numpy.radians(hdg_deg)
			break
		else:
			raise ValueError("Heading not in the correct interval")
	except ValueError:
		print("Invalid input")

while True:
	try:
		elev_deg = float(input("Enter elevation (deg) in the interval [0, 90]: "))
		if 0 <= elev_deg <= 90:
			elev = numpy.radians(elev_deg)
			break
		else:
			raise ValueError("Elevation not in the correct interval")
	except ValueError:
		print("Invalid input")

while True:
	try:
		signal_ampl_frac = float(input("Enter signal amplitude in the interval [0, 1]: "))
		if 0 <= signal_ampl_frac <= 1:
			signal_ampl = signal_ampl_frac * (BIT_DEPTH - 1) / 2
			break
		else:
			raise ValueError("Signal Amplitude not in the correct interval")
	except ValueError:
		print("Invalid input")

while True:
	try:
		noise_rms_frac = float(input("Enter noise RMS in the interval [0, 1]: "))
		if 0 <= noise_rms_frac <= 1:
			noise_rms = noise_rms_frac * (BIT_DEPTH - 1) / 2
			break
		else:
			raise ValueError("Noise RMS not in the correct interval")
	except ValueError:
		print("Invalid input")

data = numpy.array([], dtype = "<i2")

print("Generating data...")

with open(input_filename) as input_file:
	for line in input_file:
		words = line.split()

		freq_hz = int(words[0])
		if freq_hz >= 0:
			freq = 2 * numpy.pi * freq_hz / SAMPLE_RATE
		else:
			raise ValueError("Specified frequencies must be positive")

		dur_s = float(words[1])
		if dur_s >= 0:
			dur = int(dur_s * SAMPLE_RATE)
		else:
			raise ValueError("Specified durations must be positive")
		if int(len(data) / NUM_CHS) + dur > MAX_DUR:
			raise ValueError("Specified signal too long")

		ph0 = 0
		ph1 = max_travel_time * numpy.sin(hdg) * numpy.cos(elev) * freq
		ph2 = max_travel_time * numpy.cos(hdg) * numpy.cos(elev) * freq
		ph3 = max_travel_time * numpy.sin(elev) * freq

		n = numpy.arange(dur)
		segment = numpy.zeros(dur * NUM_CHS, dtype = "<i2")
		segment[0 : : NUM_CHS] = numpy.clip(signal_ampl * numpy.sin(freq * n + (freq_hz != 0) * ph0) + numpy.random.normal(scale = noise_rms, size = (dur,)), -BIT_DEPTH / 2, (BIT_DEPTH - 1) / 2)
		segment[1 : : NUM_CHS] = numpy.clip(signal_ampl * numpy.sin(freq * n + (freq_hz != 0) * ph1) + numpy.random.normal(scale = noise_rms, size = (dur,)), -BIT_DEPTH / 2, (BIT_DEPTH - 1) / 2)
		segment[2 : : NUM_CHS] = numpy.clip(signal_ampl * numpy.sin(freq * n + (freq_hz != 0) * ph2) + numpy.random.normal(scale = noise_rms, size = (dur,)), -BIT_DEPTH / 2, (BIT_DEPTH - 1) / 2)
		segment[3 : : NUM_CHS] = numpy.clip(signal_ampl * numpy.sin(freq * n + (freq_hz != 0) * ph3) + numpy.random.normal(scale = noise_rms, size = (dur,)), -BIT_DEPTH / 2, (BIT_DEPTH - 1) / 2)

		data = numpy.append(data, segment)

print("Writing data...")

with open("spoofed_dump.dat", "wb") as dump:
	for pkt_num in range(int(len(data) / (NUM_CHS * PKT_LEN))):
		pkt_data = data[(pkt_num * PKT_LEN) * NUM_CHS : ((pkt_num + 1) * PKT_LEN) * NUM_CHS]
		max_sample = numpy.max(numpy.abs(pkt_data))

		dump.write(numpy.array([pkt_num], dtype = "<u4").tobytes())
		dump.write(numpy.array([0], dtype = "<u1").tobytes())
		dump.write(numpy.array([max_sample], dtype = "<u2").tobytes())
		dump.write(pkt_data.tobytes())