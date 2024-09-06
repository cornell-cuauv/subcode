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
import pinger.const

L_plot = (int(pinger.const.DUR_INTERVAL * common.const.SAMPLE_RATE) //
    pinger.const.DECIM_FACTOR)

class TriggerPlot(plot.PlotBase):
    """This plot shows the trigger point in a ping processing interval.

    Plot updates on every ping processing interval.
    Upper subplot shows the combined amplitude of all channels in the
    downconverted signal during a full ping processing interval.
    Lower subplot shows the trigger function during the interval.
    A cursor marks the trigger point, where phases are extracted.
    """

    def plot(self, ampl, trigger_f, ping_pos):
        """Push the amplitude and trigger function for an interval.

        :param ampl: combined amplitude of all channels
        :param trigger_f: trigger function
        :param ping_pos: the phase extraction point in the interval
        """

        # Matplotlib doesn't work with CuPy arrays
        if hasattr(xp, 'asnumpy'):
            ampl = xp.asnumpy(ampl)
            trigger_f = xp.asnumpy(trigger_f)
        try:
            self._q.put_nowait((ampl, trigger_f, ping_pos))
        except queue.Full:
            pass

    @staticmethod
    def _daemon(q):
        matplotlib.use('TkAgg')
        pyplot.ioff()
        fig = pyplot.figure(figsize=(5, 5))

        indices = np.linspace(0, pinger.const.DUR_INTERVAL, num=L_plot)

        pyplot.suptitle('Trigger Plot')
        (ampl_ax, ampl_lines, ampl_cursor) = (
            TriggerPlot._define_ampl_plot(fig, indices))
        (trigger_f_ax, trigger_f_lines, trigger_f_cursor) = (
            TriggerPlot._define_trigger_f_plot(fig, indices))

        while True:
            try:
                (ampl, trigger_f, ping_pos) = q.get_nowait()

                ping_time = ping_pos / L_plot * pinger.const.DUR_INTERVAL

                plot.PlotBase._auto_ylim(ampl_ax, ampl)
                ampl_lines[0].set_ydata(ampl)
                ampl_cursor.set_xdata(ping_time)

                plot.PlotBase._auto_ylim(trigger_f_ax, trigger_f)
                trigger_f_lines[0].set_ydata(trigger_f)
                trigger_f_cursor.set_xdata(ping_time)

                pyplot.draw()
                pyplot.show(block=False)
            except queue.Empty:
                pass

            fig.canvas.flush_events()
            time.sleep(common.const.GUI_UPDATE_TIME)

    @staticmethod
    def _define_ampl_plot(fig, indices):
        # Combined amplitude subplot. X-axis limits fixed to ping
        # processing interval length, y-axis limits adjusted to
        # capture the signal with a small added margin. Cursor at the
        # phase extraction point (just past the ping rising edge).

        ax = fig.add_subplot(211)
        ax.set_ylabel('Combined Signal Amplitude')
        ax.set_xticks(np.linspace(0, pinger.const.DUR_INTERVAL, num=10))
        ax.set_xlim(0, pinger.const.DUR_INTERVAL)
        lines = ax.plot(indices, np.zeros(indices.shape), 'k-',
                        linewidth=0.5)
        cursor = ax.axvline(x=0, color='red', linestyle=':')
        return (ax, lines, cursor)

    @staticmethod
    def _define_trigger_f_plot(fig, indices):
        # Trigger function subplot. X-axis limits fixed to ping
        # processing interval length, y-axis limits adjusted to
        # capture the trigger function with a small added margin.
        # Cursor at the phase extraction point (just past the ping
        # rising edge).

        ax = fig.add_subplot(212)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Trigger Function')
        ax.set_xticks(np.linspace(0, pinger.const.DUR_INTERVAL, num=10))
        ax.set_xlim(0, pinger.const.DUR_INTERVAL)
        lines = ax.plot(indices, np.zeros(indices.shape), 'k-',
                        linewidth=0.5)
        cursor = ax.axvline(x=0, color='red', linestyle=':')
        return (ax, lines, cursor)