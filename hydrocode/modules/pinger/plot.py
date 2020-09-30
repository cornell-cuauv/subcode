import time

import numpy as np
from scipy.interpolate import interp1d

from common import pack, plot
import common.const
import pinger.const

class RawPlot(plot.Plot):
    def __init__(self, num_sig_chs, L_x, L_interval, xp=np):
        super().__init__(xp=xp)

        self._sig_pkr = pack.Packer(num_sig_chs, L_x, L_interval, xp=xp)
        self._gain_pkr = pack.Packer(1, L_x, L_interval, xp=xp)

    def push(self, x, gains):
        sig = self._sig_pkr.push(x)
        gain = self._gain_pkr.push(gains)

        if sig is not None:
            if hasattr(self._xp, 'asnumpy'):
                sig = self._xp.asnumpy(sig)
                gain = self._xp.asnumpy(gain)

            data = (sig, gain)
            self._q.put(data)

    @staticmethod
    def _worker(q):
        import matplotlib
        from matplotlib import pyplot
        matplotlib.use('TkAgg')

        pyplot.ioff()
        fig = pyplot.figure(figsize=(7, 7))

        orig_indices = np.arange(0, pinger.const.L_RAW_PLOT)
        interp_indices = np.linspace(0, pinger.const.L_RAW_PLOT - 1,
            num=1000)

        pyplot.subplot(2, 1, 1)
        pyplot.title('Signal')
        pyplot.xticks(np.arange(0, pinger.const.L_RAW_PLOT,
            pinger.const.L_RAW_PLOT // 10))
        ax_sig = pyplot.gca()
        ax_sig.set_xlim(0, pinger.const.L_RAW_PLOT - 1)
        ax_sig.set_ylim(-common.const.BIT_DEPTH // 2,
            common.const.BIT_DEPTH // 2 - 1)
        sig_lines = ax_sig.plot(interp_indices, interp_indices, 'r-',
                                interp_indices, interp_indices, 'g-',
                                interp_indices, interp_indices, 'b-',
                                interp_indices, interp_indices, 'm-',
                                linewidth = 0.5)

        pyplot.subplot(2, 1, 2)
        pyplot.title('Gain')
        pyplot.yscale('log')
        pyplot.xticks(np.arange(0, pinger.const.L_RAW_PLOT,
            pinger.const.L_RAW_PLOT // 10))
        ax_gain = pyplot.gca()
        ax_gain.set_xlim(0, pinger.const.L_RAW_PLOT - 1)
        ax_gain.set_ylim(0.9, 200)
        (gain_line,) = ax_gain.plot(orig_indices, orig_indices, 'k-',
                                    linewidth = 0.5)

        while True:
            if not q.empty():
                data = q.get()

                sig = data[0]
                L_interval = sig.shape[1]

                peak_pos = np.abs(sig).argmax() % sig.shape[1]
                print(sig[:, peak_pos])
                plot_end = peak_pos + pinger.const.L_RAW_PLOT // 2
                plot_end = np.clip(
                    plot_end, pinger.const.L_RAW_PLOT, L_interval)
                plot_start = plot_end - pinger.const.L_RAW_PLOT

                sig = sig[:, plot_start : plot_end]
                sig = interp1d(orig_indices, sig, kind='cubic')(interp_indices)

                gain = data[1]
                gain = gain[:, plot_start : plot_end]

                for ch_num in range(len(sig_lines)):
                    sig_lines[ch_num].set_ydata(sig[ch_num])
                    gain_line.set_ydata(gain[0])

                    pyplot.draw()

                pyplot.show(block=False)

            fig.canvas.flush_events()
            time.sleep(common.const.GUI_UPDATE_TIME)
