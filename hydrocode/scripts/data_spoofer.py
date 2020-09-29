#!/usr/bin/env python3

import sys

import numpy as np

sys.path.insert(0, '../modules')
from common import const

MAX_DUR = 10 ** 7

max_travel_time = const.NIPPLE_DIST / const.SOUND_SPEED * const.SAMPLE_RATE
range_top = const.BIT_DEPTH / 2 - 1
range_bottom = -const.BIT_DEPTH / 2

try:
    input_filename = sys.argv[1]
except IndexError:
    print('Input filename not specified')
    raise

while True:
    try:
        pkt_type = int(input('Enter packet type (0 - pinger, 1 - comms): '))
        if pkt_type == 0 or pkt_type == 1:
            break
        else:
            raise ValueError('Packet type must be 0 or 1')
    except ValueError:
        print('Invalid input')

while True:
    try:
        hdg_deg = float(input('Enter heading in the interval [0, 360): '))
        if 0 <= hdg_deg < 360:
            hdg = np.radians(hdg_deg)
            break
        else:
            raise ValueError('Heading not in the correct interval')
    except ValueError:
        print('Invalid input')

while True:
    try:
        elev_deg = float(input('Enter elevation in the interval [0, 90]: '))
        if 0 <= elev_deg <= 90:
            elev = np.radians(elev_deg)
            break
        else:
            raise ValueError('Elevation not in the correct interval')
    except ValueError:
        print('Invalid input')

while True:
    try:
        signal_ampl_frac = float(input(
            'Enter signal amplitude in the interval [0, 1]: '))
        if 0 <= signal_ampl_frac <= 1:
            signal_ampl = signal_ampl_frac * range_top
            break
        else:
            raise ValueError('Signal Amplitude not in the correct interval')
    except ValueError:
        print('Invalid input')

while True:
    try:
        noise_rms_frac = float(input(
            'Enter noise RMS in the interval [0, 1]: '))
        if 0 <= noise_rms_frac <= 1:
            noise_rms = noise_rms_frac * range_top
            break
        else:
            raise ValueError('Noise RMS not in the correct interval')
    except ValueError:
        print('Invalid input')

samples = list()

print('Generating data...')

with open(input_filename) as input_file:
    for line in input_file:
        words = line.split(',')

        freq_hz = int(words[0])
        if freq_hz >= 0:
            freq = 2 * np.pi * freq_hz / const.SAMPLE_RATE
        else:
            raise ValueError('Specified frequencies must be positive')

        dur_s = float(words[1])
        if dur_s >= 0:
            dur = int(dur_s * const.SAMPLE_RATE)
        else:
            raise ValueError('Specified durations must be positive')
        if len(samples) // const.NUM_CHS + dur > MAX_DUR:
            raise ValueError('Specified signal too long')

        ph = np.array([
            [0],
            [max_travel_time * np.sin(hdg) * np.cos(elev) * freq],
            [max_travel_time * np.cos(hdg) * np.cos(elev) * freq],
            [max_travel_time * np.sin(elev) * freq]])

        n = np.arange(dur)
        signal = signal_ampl * np.sin(freq * n + (freq_hz != 0) * ph)
        noise = np.random.normal(scale=noise_rms, size=(const.NUM_CHS, dur))
        signal += noise
        signal = np.clip(signal, range_bottom, range_top)
        signal = signal.astype('<i2')

        samples.append(signal)

samples = np.concatenate(samples, axis=1)

print('Writing data...')

with open('spoofed_dump.dat', 'wb') as dump_file:
    for pkt_num in range(samples.shape[1] // const.L_PKT):
        pkt_samples = samples[:, pkt_num * const.L_PKT :
            (pkt_num + 1) * const.L_PKT]
        max_sample = np.abs(pkt_samples).max()

        buff = np.array((pkt_type, pkt_num, 0, max_sample, pkt_samples),
            dtype=const.RECV_PKT_DTYPE).tobytes()

        dump_file.write(buff)