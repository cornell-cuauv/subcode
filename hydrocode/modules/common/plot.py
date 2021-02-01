import abc
from multiprocessing import Process, Queue

import numpy as np

class PlotBase:
    def __init__(self, xp=np):
        self._xp = xp

        self._q = Queue(maxsize=10)
        self._plotting_process = Process(target=self._worker, args=(self._q,))
        self._plotting_process.daemon = True
        self._plotting_process.start()

    @abc.abstractmethod
    def plot(self, x):
        pass

    @staticmethod
    @abc.abstractmethod
    def _worker(q):
        pass

    @staticmethod
    def _worker_init():
        import matplotlib
        from matplotlib import pyplot
        matplotlib.use('TkAgg')

        pyplot.ioff()
        fig = pyplot.figure(figsize=(5, 5))

        return (pyplot, fig)

    @staticmethod
    def _auto_ylim(ax, x):
        ax.set_ylim(x.min() - 0.1 * np.abs(x.min()), 1.1 * x.max())