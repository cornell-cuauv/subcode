import queue
import time

import numpy as np
from scipy.interpolate import interp1d

from common import const, crop, plot
from common.retry import retry

class GainPlot(plot.PlotBase):
    def push(self, sig, gains):
        L_interval = sig.shape[1]

        peak_pos = self._xp.abs(sig).argmax() % L_interval
        peak_pos = int(peak_pos)
        (plot_start, plot_end) = crop.find_bounds(
            L_interval, const.L_GAIN_PLOT, peak_pos)
        cursor_pos = peak_pos - plot_start

        sig = sig[:, plot_start : plot_end]
        gains = gains[:, plot_start : plot_end]

        if hasattr(self._xp, 'asnumpy'):
            sig = self._xp.asnumpy(sig)
            gains = self._xp.asnumpy(gains)

        retry(self._q.put, queue.Full)((sig, gains, cursor_pos))

    @staticmethod
    def _worker(q):
        (pyplot, fig) = plot.PlotBase._worker_init()

        orig_indices = np.arange(0, const.L_GAIN_PLOT)
        interp_indices = np.linspace(0, const.L_GAIN_PLOT - 1, num=1000)

        pyplot.suptitle('Gain Plot')
        (_, sig_lines, sig_cursor) = (
            GainPlot._define_sig_plot(pyplot, interp_indices))
        (_, gains_lines, gains_cursor) = (
            GainPlot._define_gains_plot(pyplot, orig_indices))

        while True:
            try:
                (sig, gains, cursor_pos) = q.get(block=False)

                sig = interp1d(orig_indices, sig, kind='cubic')(interp_indices)
                for ch_num in range(len(sig_lines)):
                    sig_lines[ch_num].set_ydata(sig[ch_num])
                sig_cursor.set_xdata(cursor_pos)

                gains_lines[0].set_ydata(gains[0])
                gains_cursor.set_xdata(cursor_pos)

                pyplot.draw()
                pyplot.show(block=False)
            except queue.Empty:
                pass

            fig.canvas.flush_events()
            time.sleep(const.GUI_UPDATE_TIME)

    @staticmethod
    def _define_sig_plot(pyplot, indices):
        pyplot.subplot(2, 1, 1)
        pyplot.xlabel('Sample Number')
        pyplot.ylabel('Raw Signal')
        pyplot.xticks(np.arange(0, const.L_GAIN_PLOT, const.L_GAIN_PLOT // 10))
        ax = pyplot.gca()
        ax.set_xlim(0, const.L_GAIN_PLOT - 1)
        ax.set_ylim(-const.BIT_DEPTH // 2, const.BIT_DEPTH // 2 - 1)
        lines = ax.plot(indices, indices, 'r-',
                        indices, indices, 'g-',
                        indices, indices, 'b-',
                        indices, indices, 'm-',
                        linewidth = 0.5)
        cursor = ax.axvline(x=0, color='red', linestyle=':')
        return (ax, lines, cursor)

    @staticmethod
    def _define_gains_plot(pyplot, indices):
        pyplot.subplot(2, 1, 2)
        pyplot.xlabel('Sample Number')
        pyplot.ylabel('Gain')
        pyplot.yscale('log')
        pyplot.xticks(np.arange(0, const.L_GAIN_PLOT, const.L_GAIN_PLOT // 10))
        ax = pyplot.gca()
        ax.set_xlim(0, const.L_GAIN_PLOT - 1)
        ax.set_ylim(0.9, 200)
        lines = ax.plot(indices, indices, 'k-',
                        linewidth = 0.5)
        cursor = ax.axvline(x=0, color='red', linestyle=':')
        return (ax, lines, cursor)
