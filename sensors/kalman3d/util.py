import time
from typing import Callable


def timed(f_x, *args, **kwargs):
    start = time.time()
    return f_x(*args, **kwargs), 1 / (time.time() - start)
