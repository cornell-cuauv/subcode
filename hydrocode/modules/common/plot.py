import abc
from multiprocessing import Process, Queue

class Plot:
    def __init__(self):
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