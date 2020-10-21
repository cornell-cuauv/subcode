import time

import numpy as np
from scipy.interpolate import interp1d

from common import pack, plot
import common.const
import pinger.const

class RawPlot(plot.PlotBase):
    def __init__(self, num_sig_chs, L_x, L_interval, xp=np):
        super().__init__(xp=xp)

        self._sig_pkr = pack.Packer(num_sig_chs, L_x, L_interval, xp=xp)
        self._gain_pkr = pack.Packer(1, L_x, L_interval, xp=xp)

    def push(self, x, gains):
        packed_sig = self._sig_pkr.push(x)
        packed_gains = self._gain_pkr.push(gains)

        if packed_sig is not None:
            if hasattr(self._xp, 'asnumpy'):
                packed_sig = self._xp.asnumpy(packed_sig)
                packed_gains = self._xp.asnumpy(packed_gains)

            data = (packed_sig, packed_gains)
            self._q.put(data)

    @staticmethod
    def _worker(q):
        (pyplot, fig) = plot.PlotBase._worker_init()

        orig_indices = np.arange(0, pinger.const.L_RAW_PLOT)
        interp_indices = np.linspace(0, pinger.const.L_RAW_PLOT - 1, num=1000)

        sig_lines = RawPlot._define_signal_plot(pyplot, interp_indices)
        gain_line = RawPlot._define_gain_plot(pyplot, orig_indices)

        while True:
            if not q.empty():
                data = q.get()

                sig = data[0]

                (plot_start, plot_end) = RawPlot._find_crop_interval(sig)

                sig = sig[:, plot_start : plot_end]
                sig = interp1d(orig_indices, sig, kind='cubic')(interp_indices)

                gains = data[1][0]
                gains = gains[plot_start : plot_end]

                for ch_num in range(len(sig_lines)):
                    sig_lines[ch_num].set_ydata(sig[ch_num])
                    gain_line.set_ydata(gains)

                    pyplot.draw()

                pyplot.show(block=False)

            fig.canvas.flush_events()
            time.sleep(common.const.GUI_UPDATE_TIME)

    @staticmethod
    def _define_signal_plot(pyplot, indices):
        pyplot.subplot(2, 1, 1)
        pyplot.title('Signal')
        pyplot.xticks(np.arange(0, pinger.const.L_RAW_PLOT,
            pinger.const.L_RAW_PLOT // 10))
        ax = pyplot.gca()
        ax.set_xlim(0, pinger.const.L_RAW_PLOT - 1)
        ax.set_ylim(-common.const.BIT_DEPTH // 2,
            common.const.BIT_DEPTH // 2 - 1)
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
        pyplot.xticks(np.arange(0, pinger.const.L_RAW_PLOT,
            pinger.const.L_RAW_PLOT // 10))
        ax = pyplot.gca()
        ax.set_xlim(0, pinger.const.L_RAW_PLOT - 1)
        ax.set_ylim(0.9, 200)
        (line,) = ax.plot(indices, indices, 'k-',
                          linewidth = 0.5)
        return line

    @staticmethod
    def _find_crop_interval(sig):
        L_interval = sig.shape[1]

        peak_pos = np.abs(sig).argmax() % sig.shape[1]

        plot_end = peak_pos + pinger.const.L_RAW_PLOT // 2
        plot_end = np.clip(plot_end, pinger.const.L_RAW_PLOT, L_interval)

        plot_start = plot_end - pinger.const.L_RAW_PLOT

        return (plot_start, plot_end)