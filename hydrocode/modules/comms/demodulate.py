import numpy as np

from comms import const

def decide(x, xp=np):
    x = x.reshape(x.shape[: -1] + (-1, const.SAMPLES_PER_SYM)).sum(axis=2)
    x = x.argmax(axis=0)

    return x

def decode(x, xp=np):
    symbols_per_byte = 8 // const.SYMBOL_SIZE
    assert len(x) % symbols_per_byte == 0, (
        'Symbols must yield an integer number of bytes')

    x = x.reshape(-1, symbols_per_byte)
    x *= 2 ** xp.flip(const.SYMBOL_SIZE * xp.arange(symbols_per_byte))
    x = x.sum(axis=1)

    return x.astype('B').tobytes()