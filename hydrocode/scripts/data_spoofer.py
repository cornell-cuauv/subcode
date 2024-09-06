#!/usr/bin/env python3

"""Simple hydrophones data simulator

Takes as input a CSV file containing a sequence of pulses where the
first column represents the frequency (Hz) and the second column the
duration (s). In addition, the user specifies from keyboard parameters
such as heading/elevation. The result is a dump replayable by the same
script that replays real data dumps.

Must be called with the input file name as an argument.

This is only useful for basic testing, since it can add gaussian noise,
but doesn't simulate multipath propagation.
"""

from os import path
import sys

import numpy as np

sys.path.insert(0, path.join(
    path.dirname(path.dirname(path.realpath(__file__))), 'modules'))
from hydrocode.modules.common import const

# maximum simulation time (samples), not infinite because the signal is created
# in memory, then written to disk
MAX_DUR = 10 ** 7

max_travel_time = const.NIPPLE_DIST / const.SOUND_SPEED * const.SAMPLE_RATE
range_top = const.BIT_DEPTH / 2 - 1
range_bottom = -const.BIT_DEPTH / 2

try:
    input_filename = sys.argv[1]
except IndexError:
    raise Exception('Input filename not specified')

while True:
    try:
        pkt_type = int(input('Enter packet type - 0 (pinger) or 1 (comms): '))
        if not (pkt_type == 0 or pkt_type == 1):
            raise ValueError('Packet type must be 0 or 1')
        break
    except ValueError as e:
        print(e)

while True:
    try:
        hdg_deg = float(input('Enter heading in the interval [0, 360): '))
        if not (0 <= hdg_deg < 360):
            raise ValueError('Heading not in the correct interval')
        hdg = np.radians(hdg_deg) - const.ENCLOSURE_OFFSET
        break
    except ValueError as e:
        print(e)

while True:
    try:
        elev_deg = float(input('Enter elevation in the interval [-90, 90]: '))
        if not (-90 <= elev_deg <= 90):
            raise ValueError('Elevation not in the correct interval')
        elev = np.radians(elev_deg)
        break
    except ValueError as e:
        print(e)

while True:
    try:
        signal_ampl_frac = float(input(
            'Enter signal amplitude in the interval [0, 1]: '))
        if not (0 <= signal_ampl_frac <= 1):
            raise ValueError('Signal amplitude not in the correct interval')
        signal_ampl = signal_ampl_frac * range_top
        break
    except ValueError as e:
        print(e)

while True:
    try:
        noise_rms_frac = float(input(
            'Enter noise RMS in the interval [0, 1]: '))
        if not (0 <= noise_rms_frac <= 1):
            raise ValueError('Noise RMS not in the correct interval')
        noise_rms = noise_rms_frac * range_top
        break
    except ValueError as e:
        print(e)

print('Generating data...')

with open(input_filename) as input_file:
    samples = []
    for line in input_file:
        words = line.split(',')

        freq_hz = int(words[0])
        if freq_hz < 0:
            raise ValueError('Specified frequencies must be positive')
        freq = 2 * np.pi * freq_hz / const.SAMPLE_RATE

        dur_s = float(words[1])
        if dur_s < 0:
            raise ValueError('Specified durations must be positive')
        dur = int(dur_s * const.SAMPLE_RATE)

        if len(samples) // const.NUM_CHS + dur > MAX_DUR:
            raise ValueError('Specified signal too long')

        # phases at the four elements, obtained from heading/elevation angles
        ph = np.array([
            [0],
            [max_travel_time * np.sin(hdg) * np.cos(-elev) * freq],
            [max_travel_time * np.cos(hdg) * np.cos(-elev) * freq],
            [max_travel_time * np.sin(-elev) * freq]])

        # although phases are realistic, the fact that the signal arrives at
        # different times at the elements is not simulated
        n = np.arange(dur)
        signal = signal_ampl * np.sin(freq * n + (freq_hz != 0) * ph)
        noise = np.random.normal(scale=noise_rms, size=(const.NUM_CHS, dur))
        signal += noise
        signal = np.clip(signal, range_bottom, range_top)
        signal = signal.astype('<i2')

        samples.append(signal)

samples = np.concatenate(samples, axis=1)

# switch channels [0, 1] -> [1, 0], [2, 3] -> [3, 2]
# (minor screw-up on the hydrophones board)
if pkt_type == 0:
    samples[[0, 1]] = samples[[1, 0]]
    samples[[2, 3]] = samples[[3, 2]]

print('Writing data...')

with open('spoofed_dump.dat', 'wb') as dump_file:
    for pkt_num in range(samples.shape[1] // const.L_PKT):
        pkt_samples = samples[:, pkt_num * const.L_PKT :
            (pkt_num + 1) * const.L_PKT]
        max_sample = np.abs(pkt_samples).max()

        buff = np.array((pkt_num, pkt_samples, max_sample, pkt_type, 0),
            dtype=const.SAMPLE_PKT_DTYPE).tobytes()

        dump_file.write(buff)