"""Hardcoded constants"""

DECIM_FACTOR = 8 # decimation factor after downconversion
DUR_INTERVAL = 2.2 # duration of ping processing and gain control intervals (s)
FIR_ORDER = 256 # order of the gaussian lowpass FIR used during downconversion
L_FIR_BLOCK = 16384 # amount of samples per filtering operation
L_PING_PLOT = 100 # length of the ping plot (samples after decimation)
L_SEARCH = 5000 # length of the ping search interval (samples after decimation)
RECV_PORT = 49152 # port where hydrophones board sends packets
SEND_PORT = 49152 # port where hydrophones board receives configuration packets
STOPBAND = 7500 # width of the downconversion filter
USUAL_FREQS = [25000, 30000, 35000, 40000] # RoboSub pinger frequencies (Hz)