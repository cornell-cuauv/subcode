import abc
from multiprocessing import Process, Queue

import numpy as np

class PlotBase:
    """Base class for plots."""

    def __init__(self):
        """Constructor."""

        self._q = Queue(maxsize=10)
        self._plotting_process = Process(target=self._daemon,
            args=(self._q,), daemon=True)
        self._plotting_process.start()

    @abc.abstractmethod
    def plot(self, x):
        """Push the signals to plot.

        :param x: signals to plot, must be an array of shape
            (numner of signals, number of samples in each signal)
        """

        pass

    @staticmethod
    @abc.abstractmethod
    def _daemon(q):
        # Need to plot in a different process because this is pretty CPU
        # intensive, would momentarily lose samples from the hydrophones
        # board if we did this in the main process.

        pass

    @staticmethod
    def _auto_ylim(ax, x):
        # Set y-axis limits such that the full signal is visible, with
        # small margins above and below.

        ax.set_ylim(x.min() - 0.1 * np.abs(x.min()), 1.1 * x.max())