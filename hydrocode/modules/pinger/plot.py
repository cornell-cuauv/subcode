import time

import numpy as np
from scipy.interpolate import interp1d

from common import pack, plot
import common.const
import pinger.const

class RawPlot(plot.Plot):
    def __init__(self, num_sig_chs, L_x, L_interval, xp=np):
        super().__init__()

        assert num_sig_chs >= 1, 'Plot must have at least one signal channel'
        assert L_x > 0, 'Input block length must be at least 1'
        assert L_interval > 0, 'Interval length must be at least 1'
        assert L_interval >= L_x, (
            'Interval must be at least as large as the input blocks')

        self._xp = xp

        self._sig_pkr = pack.Packer(num_sig_chs, L_x, L_interval, xp=self._xp)
        self._gain_pkr = pack.Packer(1, L_x, L_interval, xp=self._xp)

    def push(self, x, gain_array):
        sig = self._sig_pkr.push(x)
        gain = self._gain_pkr.push(gain_array)

        if sig is not None:
            if hasattr(self._xp, 'as_numpy'):
                sig = xp.as_numpy(sig)
                gain = xp.as_numpy(gain)

            data = (sig, gain)
            self._q.put(data)

    @staticmethod
    def _worker(q):
        import matplotlib
        from matplotlib import pyplot
        matplotlib.use('TkAgg')

        pyplot.ioff()
        fig = pyplot.figure(figsize=(7, 7))

        orig_indices = np.arange(0, pinger.const.RAW_PLOT_LEN)
        interp_indices = np.linspace(0, pinger.const.RAW_PLOT_LEN - 1,
            num=1000)

        pyplot.subplot(2, 1, 1)
        pyplot.title('Signal')
        pyplot.xticks(np.arange(0, pinger.const.RAW_PLOT_LEN,
            pinger.const.RAW_PLOT_LEN // 10))
        ax_sig = pyplot.gca()
        ax_sig.set_xlim(0, pinger.const.RAW_PLOT_LEN - 1)
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
        pyplot.xticks(np.arange(0, pinger.const.RAW_PLOT_LEN,
            pinger.const.RAW_PLOT_LEN // 10))
        ax_gain = pyplot.gca()
        ax_gain.set_xlim(0, pinger.const.RAW_PLOT_LEN - 1)
        ax_gain.set_ylim(0.9, 200)
        (gain_line,) = ax_gain.plot(orig_indices, orig_indices, 'k-',
                                    linewidth = 0.5)

        pyplot.draw()

        while True:
            if not q.empty():
                data = q.get()

                sig = data[0]
                peak_pos = np.abs(sig).argmax() % sig.shape[1]
                sig = sig[:, peak_pos - pinger.const.RAW_PLOT_LEN // 2 :
                    peak_pos + (pinger.const.RAW_PLOT_LEN + 1) // 2]
                sig = interp1d(orig_indices, sig, kind='cubic')(interp_indices)

                gain = data[1]
                gain = gain[:, peak_pos - pinger.const.RAW_PLOT_LEN // 2 :
                    peak_pos + (pinger.const.RAW_PLOT_LEN + 1) // 2]

                for ch_num in range(len(sig_lines)):
                    sig_lines[ch_num].set_ydata(sig[ch_num])
                    ax_sig.draw_artist(sig_lines[ch_num])

                    gain_line.set_ydata(gain[0])
                    ax_gain.draw_artist(gain_line)

                pyplot.show(block=False)

            fig.canvas.flush_events()
            time.sleep(common.const.GUI_UPDATE_TIME)