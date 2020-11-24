import queue
import time

import numpy as np

from common import plot
from common.retry import retry
import common.const
import pinger.const

class TriggerPlot(plot.PlotBase):
    def plot(self, ampl, trigger_f, ping_pos):
        if hasattr(self._xp, 'asnumpy'):
            ampl = self._xp.asnumpy(ampl)
            trigger_f = self._xp.asnumpy(trigger_f)

        retry(self._q.put, queue.Full)(
            (ampl, trigger_f, ping_pos), timeout=0.1)

    @staticmethod
    def _worker(q):
        (pyplot, fig) = plot.PlotBase._worker_init()

        L_interval = (int(pinger.const.DUR_INTERVAL * common.const.SAMPLE_RATE)
            // pinger.const.DECIM_FACTOR)
        indices = np.linspace(0, pinger.const.DUR_INTERVAL, num=L_interval)

        pyplot.suptitle('Trigger Plot')
        (ampl_ax, ampl_lines, ampl_cursor) = (
            TriggerPlot._define_ampl_plot(fig, indices))
        (trigger_f_ax, trigger_f_lines, trigger_f_cursor) = (
            TriggerPlot._define_trigger_f_plot(fig, indices))

        while True:
            try:
                (ampl, trigger_f, ping_pos) = q.get(block=False)

                ping_time = ping_pos / L_interval * pinger.const.DUR_INTERVAL

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
        ax = fig.add_subplot(212)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Trigger Function')
        ax.set_xticks(np.linspace(0, pinger.const.DUR_INTERVAL, num=10))
        ax.set_xlim(0, pinger.const.DUR_INTERVAL)
        lines = ax.plot(indices, np.zeros(indices.shape), 'k-',
                        linewidth=0.5)
        cursor = ax.axvline(x=0, color='red', linestyle=':')
        return (ax, lines, cursor)
