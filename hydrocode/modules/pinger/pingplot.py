import queue
import time

try:
    import cupy as xp
except ImportError:
    import numpy as xp
import matplotlib
from matplotlib import pyplot
import numpy as np
from scipy.interpolate import interp1d

from common import crop, plot
import common.const
import pinger.const

class PingPlot(plot.PlotBase):
    """This plot helps ensure phase extraction at the ping rising edge.

    Plot updates on every ping processing interval.
    Upper subplot shows the amplitudes of the channels in the
    downconverted signal (short snippet centered around the ping rising
    edge if triggering is correct).
    Lower subplot shows the phases of the channels in the downconverted
    signal during the same snippet.
    """

    def plot(self, x, ping_pos):
        """Push the downconverted signal for a ping processing interval.

        :param x: downconverted signal
        :param ping_pos: the phase extraction point in the interval
        """

        L_interval = x.shape[1]

        # find the short snippet around the ping rising edge
        (plot_start, plot_end) = crop.find_bounds(
            L_interval, pinger.const.L_PING_PLOT, ping_pos)
        cursor_pos = ping_pos - plot_start

        x = x[:, plot_start : plot_end]

        # Matplotlib doesn't work with CuPy arrays
        if hasattr(xp, 'asnumpy'):
            x = xp.asnumpy(x)
        try:
            self._q.put_nowait((x, cursor_pos))
        except queue.Full:
            pass

    @staticmethod
    def _daemon(q):
        matplotlib.use('TkAgg') # only backend that works on macOS
        pyplot.ioff()
        fig = pyplot.figure(figsize=(5, 5))

        # interpolate signal to 1000 points so it looks smooth even
        # though it contains frequencies relatively close to half the
        # sampling rate
        interp_indices = np.linspace(0, pinger.const.L_PING_PLOT - 1, num=1000)

        pyplot.suptitle('Ping Plot')
        (ampl_ax, ampl_lines, ampl_cursor) = (
            PingPlot._define_ampl_plot(fig, interp_indices))
        (phase_ax, phase_lines, phase_cursor) = (
            PingPlot._define_phase_plot(fig, interp_indices))

        while True:
            try:
                (x, cursor_pos) = q.get_nowait()

                # cubic splines interpolation
                x = PingPlot._interp_complex(x, interp_indices)

                ampl = np.abs(x)
                plot.PlotBase._auto_ylim(ampl_ax, ampl)
                for ch_num in range(ampl.shape[0]):
                    ampl_lines[ch_num].set_ydata(ampl[ch_num])
                ampl_cursor.set_xdata(cursor_pos)

                phase = np.angle(x)
                for ch_num in range(phase.shape[0]):
                    phase_lines[ch_num].set_ydata(phase[ch_num])
                phase_cursor.set_xdata(cursor_pos)

                pyplot.draw()
                pyplot.show(block=False)
            except queue.Empty:
                pass

            fig.canvas.flush_events()
            time.sleep(common.const.GUI_UPDATE_TIME)

    @staticmethod
    def _define_ampl_plot(fig, indices):
        # Amplitude subplot. One color for each of four channels, x-axis
        # limits fixed to snippet length, y-axis limits adjusted to
        # capture the signal with a small added margin. Cursor at the
        # phase extraction point (just past the ping rising edge).

        ax = fig.add_subplot(211)
        ax.set_ylabel('Signal Amplitude')
        ax.set_xticks(np.arange(
            0, pinger.const.L_PING_PLOT, pinger.const.L_PING_PLOT // 10))
        ax.set_xlim(0, pinger.const.L_PING_PLOT - 1)
        lines = ax.plot(indices, np.zeros(indices.shape), 'r-',
                        indices, np.zeros(indices.shape), 'g-',
                        indices, np.zeros(indices.shape), 'b-',
                        indices, np.zeros(indices.shape), 'm-',
                        linewidth=0.5)
        cursor = ax.axvline(x=0, color='red', linestyle=':')
        return (ax, lines, cursor)

    @staticmethod
    def _define_phase_plot(fig, indices):
        # Phase subplot. One color for each of four channels, x-axis
        # limits fixed to snippet length, y-axis limits fixed to
        # slightly over [-pi, pi). Cursor at the phase extraction point
        # (just past the ping rising edge).

        ax = fig.add_subplot(212)
        ax.set_xlabel('Decimated Sample Number')
        ax.set_ylabel('Signal Phase')
        ax.set_xticks(np.arange(
            0, pinger.const.L_PING_PLOT, pinger.const.L_PING_PLOT // 10))
        ax.set_xlim(0, pinger.const.L_PING_PLOT - 1)
        ax.set_ylim(-4, 4)
        lines = ax.plot(indices, np.zeros(indices.shape), 'r-',
                        indices, np.zeros(indices.shape), 'g-',
                        indices, np.zeros(indices.shape), 'b-',
                        indices, np.zeros(indices.shape), 'm-',
                        linewidth=0.5)
        cursor = ax.axvline(x=0, color='red', linestyle=':')
        return (ax, lines, cursor)

    @staticmethod
    def _interp_complex(x, interp_indices):
        # Interpolate complex signal using cubic splines. This is not
        # exact, because usual packages don't support complex
        # interpolation. However, interpolating the real and complex
        # components individually seems to be a good approximation.

        orig_indices = np.arange(0, pinger.const.L_PING_PLOT)

        real = x.real
        real = interp1d(orig_indices, real, kind='cubic')(interp_indices)

        imag = x.imag
        imag = interp1d(orig_indices, imag, kind='cubic')(interp_indices)

        return real + 1j * imag