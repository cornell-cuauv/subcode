import time

import numpy as np
from scipy.interpolate import interp1d

from common import const, crop, plot

class GainPlot(plot.PlotBase):
    def push(self, sig, gains):
        if hasattr(self._xp, 'asnumpy'):
            sig = self._xp.asnumpy(sig)
            gains = self._xp.asnumpy(gains)

        self._q.put((sig, gains))

    @staticmethod
    def _worker(q):
        (pyplot, fig) = plot.PlotBase._worker_init()

        orig_indices = np.arange(0, const.L_GAIN_PLOT)
        interp_indices = np.linspace(0, const.L_GAIN_PLOT - 1, num=1000)

        sig_lines = GainPlot._define_signal_plot(pyplot, interp_indices)
        gain_lines = GainPlot._define_gain_plot(pyplot, orig_indices)

        while True:
            if not q.empty():
                (sig, gains) = q.get()

                L_interval = sig.shape[1]
                peak_pos = np.abs(sig).argmax() % sig.shape[1]
                (plot_start, plot_end) = crop.find_bounds(
                    L_interval, const.L_GAIN_PLOT, peak_pos)

                sig = sig[:, plot_start : plot_end]
                sig = interp1d(orig_indices, sig, kind='cubic')(interp_indices)

                gains = gains[:, plot_start : plot_end]

                for ch_num in range(len(sig_lines)):
                    sig_lines[ch_num].set_ydata(sig[ch_num])
                gain_lines[0].set_ydata(gains[0])

                pyplot.draw()
                pyplot.show(block=False)

            fig.canvas.flush_events()
            time.sleep(const.GUI_UPDATE_TIME)

    @staticmethod
    def _define_signal_plot(pyplot, indices):
        pyplot.subplot(2, 1, 1)
        pyplot.title('Raw Signal')
        pyplot.xticks(np.arange(0, const.L_GAIN_PLOT, const.L_GAIN_PLOT // 10))
        ax = pyplot.gca()
        ax.set_xlim(0, const.L_GAIN_PLOT - 1)
        ax.set_ylim(-const.BIT_DEPTH // 2, const.BIT_DEPTH // 2 - 1)
        lines = ax.plot(indices, indices, 'r-',
                        indices, indices, 'g-',
                        indices, indices, 'b-',
                        indices, indices, 'm-',
                        linewidth = 0.5)
        return lines

    @staticmethod
    def _define_gain_plot(pyplot, indices):
        pyplot.subplot(2, 1, 2)
        pyplot.title('Gain')
        pyplot.yscale('log')
        pyplot.xticks(np.arange(0, const.L_GAIN_PLOT, const.L_GAIN_PLOT // 10))
        ax = pyplot.gca()
        ax.set_xlim(0, const.L_GAIN_PLOT - 1)
        ax.set_ylim(0.9, 200)
        lines = ax.plot(indices, indices, 'k-',
                        linewidth = 0.5)
        return lines

