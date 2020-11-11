import queue
import time

import numpy as np
from scipy.interpolate import interp1d

from common import crop, plot
from common.retry import retry
import common.const
import pinger.const

class PingPlot(plot.PlotBase):
    def push(self, x, ping_pos):
        L_interval = x.shape[1]

        (plot_start, plot_end) = crop.find_bounds(
            L_interval, pinger.const.L_PING_PLOT, ping_pos)
        cursor_pos = ping_pos - plot_start

        x = x[:, plot_start : plot_end]

        if hasattr(self._xp, 'asnumpy'):
            x = self._xp.asnumpy(x)

        retry(self._q.put, queue.Full)((x, cursor_pos))

    @staticmethod
    def _worker(q):
        (pyplot, fig) = plot.PlotBase._worker_init()

        interp_indices = np.linspace(0, pinger.const.L_PING_PLOT - 1, num=1000)

        pyplot.suptitle('Ping Plot')
        (ampl_ax, ampl_lines, ampl_cursor) = (
            PingPlot._define_ampl_plot(pyplot, interp_indices))
        (phase_ax, phase_lines, phase_cursor) = (
            PingPlot._define_phase_plot(pyplot, interp_indices))

        while True:
            try:
                (x, cursor_pos) = q.get(block=False)

                x = PingPlot._interp_complex(x, interp_indices)

                ampl = np.abs(x)
                plot.PlotBase._auto_ylim(ampl_ax, ampl)
                for ch_num in range(len(ampl_lines)):
                    ampl_lines[ch_num].set_ydata(ampl[ch_num])
                ampl_cursor.set_xdata(cursor_pos)

                phase = np.angle(x)
                for ch_num in range(len(phase_lines)):
                    phase_lines[ch_num].set_ydata(phase[ch_num])
                phase_cursor.set_xdata(cursor_pos)

                pyplot.draw()
                pyplot.show(block=False)
            except queue.Empty:
                pass

            fig.canvas.flush_events()
            time.sleep(common.const.GUI_UPDATE_TIME)

    @staticmethod
    def _define_ampl_plot(pyplot, indices):
        pyplot.subplot(2, 1, 1)
        pyplot.xlabel('Decimated Sample Number')
        pyplot.ylabel('Signal Amplitude')
        pyplot.xticks(np.arange(
            0, pinger.const.L_PING_PLOT, pinger.const.L_PING_PLOT // 10))
        ax = pyplot.gca()
        ax.set_xlim(0, pinger.const.L_PING_PLOT - 1)
        lines = ax.plot(indices, indices, 'r-',
                        indices, indices, 'g-',
                        indices, indices, 'b-',
                        indices, indices, 'm-',
                        linewidth = 0.5)
        cursor = ax.axvline(x=0, color='red', linestyle=':')
        return (ax, lines, cursor)

    @staticmethod
    def _define_phase_plot(pyplot, indices):
        pyplot.subplot(2, 1, 2)
        pyplot.xlabel('Decimated Sample Number')
        pyplot.ylabel('Signal Phase')
        pyplot.xticks(np.arange(
            0, pinger.const.L_PING_PLOT, pinger.const.L_PING_PLOT // 10))
        ax = pyplot.gca()
        ax.set_xlim(0, pinger.const.L_PING_PLOT - 1)
        ax.set_ylim(-4, 4)
        lines = ax.plot(indices, indices, 'r-',
                        indices, indices, 'g-',
                        indices, indices, 'b-',
                        indices, indices, 'm-',
                        linewidth = 0.5)
        cursor = ax.axvline(x=0, color='red', linestyle=':')
        return (ax, lines, cursor)

    @staticmethod
    def _interp_complex(x, interp_indices):
        orig_indices = np.arange(0, pinger.const.L_PING_PLOT)

        real = x.real
        real = interp1d(orig_indices, real, kind='cubic')(interp_indices)

        imag = x.imag
        imag = interp1d(orig_indices, imag, kind='cubic')(interp_indices)

        return real + 1j * imag
