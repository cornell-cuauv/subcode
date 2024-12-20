import queue
import time

try:
    import cupy as xp
except ImportError:
    import numpy as xp
import matplotlib
from matplotlib import pyplot
import numpy as np

from hydrocode.modules.common import plot
import common.const
import comms.const

L_head = len(comms.const.PN_SEQ) + 1
L_msg = comms.const.MSG_BYTES * 8 // comms.const.SYMBOL_SIZE
L_plot = (L_head + L_msg) * comms.const.L_SYM

class CorrelationPlot(plot.PlotBase):
    """This plot shows PN code correlation peaks that cause triggering.

    Plot updates for every triggering event, showing a snippet that
    starts when the PN correlation output first exceeds the dynamic
    threshold.
    Upper subplot shows the correlator input.
    Lower subplot shows the PN code correlation output, the orthogonal
    code correlation output, and the dynamic threshold.
    """

    def plot(self, corr_in, corr_pn, corr_orth, thresh):
        """Push the correlator input and outputs to plot.

        :param corr_in: correlator input
        :param corr_pn: PN code correlation output
        :param corr_orth: orthogonal PN code correlation output
        :param thresh: dynamic threshold
        """

        # Matplotlib doesn't work with CuPy arrays
        if hasattr(xp, 'asnumpy'):
            corr_in = xp.asnumpy(corr_in)
            corr_pn = xp.asnumpy(corr_pn)
            corr_orth = xp.asnumpy(corr_orth)
            thresh = xp.asnumpy(thresh)
        try:
            self._q.put_nowait((corr_in, corr_pn, corr_orth, thresh))
        except queue.Full:
            pass

    @staticmethod
    def _daemon(q):
        matplotlib.use('TkAgg') # only backend that works on macOS
        pyplot.ioff()
        fig = pyplot.figure(figsize=(5, 5))

        indices = np.arange(0, L_plot)

        pyplot.suptitle('Correlation Plot')
        (corr_in_ax, corr_in_lines) = (
            CorrelationPlot._define_corr_in_plot(fig, indices))
        (corr_results_ax, corr_results_lines) = (
            CorrelationPlot._define_corr_results_plot(fig, indices))

        while True:
            try:
                (corr_in, corr_pn, corr_orth, thresh) = q.get_nowait()

                plot.PlotBase._auto_ylim(corr_in_ax, corr_in)
                corr_in_lines[0].set_ydata(corr_in[0])

                plot.PlotBase._auto_ylim(corr_results_ax,
                    np.concatenate((corr_pn, corr_orth, thresh)))
                corr_results_lines[0].set_ydata(corr_pn[0])
                corr_results_lines[1].set_ydata(corr_orth[0])
                corr_results_lines[2].set_ydata(thresh[0])

                pyplot.draw()
                pyplot.show(block=False)
            except queue.Empty:
                pass

            fig.canvas.flush_events()
            time.sleep(common.const.GUI_UPDATE_TIME)

    @staticmethod
    def _define_corr_in_plot(fig, indices):
        # Correlation input subplot. X-axis limits fixed to snippet
        # length, y-axis limits adjusted to capture the signal with a
        # small added margin.

        ax = fig.add_subplot(211)
        ax.set_ylabel('Correlation Input')
        ax.set_xticks(np.arange(0, L_plot, L_plot // 10))
        ax.set_xlim(0, L_plot - 1)
        lines = ax.plot(indices, np.zeros(indices.shape), 'k-',
                        linewidth=0.5)
        return (ax, lines)

    @staticmethod
    def _define_corr_results_plot(fig, indices):
        # Correlation outputs subplot. Different colors for the two
        # outputs and the dynamic threshold, x-axis limits fixed to
        # snippet length, y-axis limits adjusted to capture the signals
        # with a small added margin.

        ax = fig.add_subplot(212)
        ax.set_xlabel('Decimated Sample Number')
        ax.set_ylabel('Correlation Results')
        ax.set_xticks(np.arange(0, L_plot, L_plot // 10))
        ax.set_xlim(0, L_plot - 1)
        lines = ax.plot(indices, np.zeros(indices.shape), 'g-',
                        indices, np.zeros(indices.shape), 'r-',
                        indices, np.zeros(indices.shape), 'b-',
                        linewidth=0.5)
        ax.legend(('PN Code Correlation', 'Orthogonal Code Correlation',
            'Threshold'), fontsize='x-small')
        return (ax, lines)