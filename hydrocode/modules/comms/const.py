import os

DECIM_FACTOR = 1024 # decimation factor after downconversion
DUR_GAIN_INTERVAL = 2.2 # duration of gain control interval (s)
BANDWIDTH = 3000 # FSK transmission bandwidth (Hz)
FIR_ORDER = 1024 # order of the gaussian lowpass FIR used during downconversion
L_FIR_BLOCK = 16384 # amount of samples per filtering operation
L_SYM = 32 # symbol length (samples after decimation)
L_THRESH_CALC = 256 # length of the dynamic treshold calculation interval
MSG_BYTES = 8 # message size (bytes)
RECV_PORT = 49153 # port where hydrophones board sends packets
SEND_PORT = 49153 # port where hydrophones board receives configuration packets
SERIAL_UPDATE_TIME = 0.01 # polling interval for Serial variables (s)
SQUELCH_THRESH = 100 # fixed threshold that the signal must also exceed
SYMBOL_SIZE = 2 # number of bits encoded per symbol
SYMBOL_STOPBAND_FRAC = 0.75 # FIR width (fraction of symbol spacing)
THRESHOLD_FACTOR = 3 # ugly multiplicative factor for the dynamic threshold

# center frequencies for Tx/Rx, different on the two subs to avoid interference
if os.environ['CUAUV_VEHICLE_TYPE'] == "mainsub":
    TX_FREQ = 48000
    RX_FREQ = 54000
else:
    TX_FREQ = 54000
    RX_FREQ = 48000

# PN code transmitted before message to enable detection and synchronization
PN_SEQ = [1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, -1, 1, -1, -1, -1, -1, 1,
    -1, 1, -1, 1, 1, 1, -1, 1, 1, -1, -1, -1]

# orthogonal PN code used to estimate noise level and set dynamic threshold
ORTH_SEQ = [1, 1, 1, 1, 1, -1, -1, 1, -1, -1, 1, 1, -1, -1, -1, -1, 1, -1, 1,
    1, -1, 1, -1, 1, -1, -1, -1, 1, 1, 1, -1]