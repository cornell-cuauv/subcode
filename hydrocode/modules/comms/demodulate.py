try:
    import cupy as xp
except ImportError:
    import numpy as xp

def decide(x, L_sym):
    """Decide the sequence of symbols from the downconversion results.

    The signal is split into symbols based on the known symbol length.
    Then, for each section, the samples are summed, and the symbol type
    whose channel has the greatest total amplitude is chosen.

    :param x: array where each row represents the samples in one
        downconversion channel (corresponding to one symbol type)
    :param L_sym: symbol length (samples after decimation)
    :return: the sequence of symbols
    """

    assert L_sym >= 1, 'There must be at least one sample per symbol'

    assert x.shape[1] % L_sym == 0, (
        'Input must yield an integer number of symbols')

    x = x.reshape(x.shape[: -1] + (-1, L_sym)).sum(axis=2)
    x = x.argmax(axis=0)

    return x

def decode(x, symbol_size):
    """Decode a sequence of symbols into bytes.

    E.g. [0, 1, 2, 3] -> [00011011] for symbol_size = 2
         [0, 1, 2, 3] -> [00000001, 00100011] for symbol_size = 4
    Only works for sequences that encode an integer number of bytes.

    :param x: the sequence of symbols, can't contain values greater than
        2 ^ symbol_size - 1
    :param symbol_size: number of bits encoded per symbol
    :return: the encoded bytes
    """

    assert symbol_size >= 1, 'Each symbol must encode at least one bit'

    assert len(x) % (8 // symbol_size) == 0, (
        'Symbols must yield an integer number of bytes')

    symbols_per_byte = 8 // symbol_size

    x = x.reshape(-1, symbols_per_byte)
    x *= 2 ** xp.flip(symbol_size * xp.arange(symbols_per_byte), axis=0)
    x = x.sum(axis=1)

    return x.astype('B').tobytes()