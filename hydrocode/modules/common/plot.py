import abc
from multiprocessing import Process, Queue

import numpy as np

class Plot:
    def __init__(self, xp=np):
        self._xp = xp

        self._q = Queue()
        self._plotting_process = Process(target=self._worker, args=(self._q,))
        self._plotting_process.start()

    @abc.abstractmethod
    def push(self, x):
        pass

    @staticmethod
    @abc.abstractmethod
    def _worker(q):
        pass