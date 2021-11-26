"""Hardcoded constants"""

import math
import os

import numpy as np

BIT_DEPTH = 16384 # number of quantization levels for the hydrophones ADC
BOARD_ADDR = '192.168.93.102' # IP address for hydrophones board
CLIP_THRESH = 8000 # highest tolerable signal amplitude
GAIN_VALUES = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128] # PGA gains
GUI_UPDATE_TIME = 0.1 # update time for plot GUIs (s)
L_GAIN_PLOT = 70 # length of gain plot (samples)
L_PKT = 62 # length of hydrophones UDP packet (samples for each channel)
NIPPLE_DIST = 0.01778 # hydrophone array baseline (m)
NUM_CHS = 4 # number of channels on the hydrophones board
PKTS_PER_RECV = 256 # number of packets to receive in driver for one call
SAMPLE_RATE = 153061 # ADC sampling rate (samples/s)
SOUND_SPEED = 1481 # speed of sound in water (m/s)
USE_4CHS = False # set to True if experimenting with four hydrophone array

# enclosure heading offset (rad), potentially different on the two subs
if os.environ['CUAUV_VEHICLE_TYPE'] == 'mainsub':
    ENCLOSURE_OFFSET = -math.pi / 2
else:
    ENCLOSURE_OFFSET = 0

# structure of sample packets sent by hydrophones board
SAMPLE_PKT_DTYPE = np.dtype([
    ('pkt_num', '<i4'),
    ('samples', str((NUM_CHS, L_PKT)) + '<i2'),
    ('max_sample', '<i2'),
    ('pkt_type', '<i1'),
    ('gain_lvl', '<i1')
])

# structure of configuration packets sent by host to hydrophones board
CONF_PKT_DTYPE = np.dtype([
    ('reset', '?'),
    ('autogain', '?'),
    ('man_gain_lvl', '<i1')
])