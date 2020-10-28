import time

import numpy as np
from scipy.interpolate import interp1d

from common import crop, plot
import common.const
import pinger.const

class TriggerPlot(plot.PlotBase):
    def push(self, ampl, trigger_function, sig, ping_pos):
        if hasattr(self._xp, 'asnumpy'):
            ampl = self._xp.asnumpy(ampl)
            trigger_function = self._xp.asnumpy(trigger_function)
            sig = self._xp.asnumpy(sig)

        self._q.put((ampl, trigger_function, sig, ping_pos))

    @staticmethod
    def _worker(q):
        (pyplot, fig) = plot.PlotBase._worker_init()

        L_interval = (int(pinger.const.DUR_INTERVAL * common.const.SAMPLE_RATE)
            // pinger.const.DECIM_FACTOR)
        indices = np.arange(0, L_interval)

        orig_zoom_indices = np.arange(0, pinger.const.L_TRIGGER_ZOOM_PLOT)
        interp_zoom_indices = np.linspace(
            0, pinger.const.L_TRIGGER_ZOOM_PLOT - 1, num=1000)

        (ampl_ax, ampl_lines) = (
            TriggerPlot._define_ampl_plot(pyplot, indices))
        (trigger_function_ax, trigger_function_lines) = (
            TriggerPlot._define_trigger_function_plot(pyplot, indices))
        (zoom_ax, zoom_lines) = (
            TriggerPlot._define_zoom_plot(pyplot, interp_zoom_indices))

        while True:
            if not q.empty():
                (ampl, trigger_function, sig, ping_pos) = q.get()

                (zoom_start, zoom_end) = crop.find_bounds(
                    L_interval, pinger.const.L_TRIGGER_ZOOM_PLOT, ping_pos)
                zoom = sig[:, zoom_start : zoom_end]
                zoom = interp1d(orig_zoom_indices, zoom, kind='cubic')(
                    interp_zoom_indices)

                ampl_lines[0].set_ydata(ampl)
                trigger_function_lines[0].set_ydata(trigger_function)
                for ch_num in range(len(zoom_lines)):
                    zoom_lines[ch_num].set_ydata(zoom[ch_num])

                plot.PlotBase._auto_ylim(ampl_ax, ampl)
                plot.PlotBase._auto_ylim(trigger_function_ax, trigger_function)
                plot.PlotBase._auto_ylim(zoom_ax, zoom)

                pyplot.draw()
                pyplot.show(block=False)

            fig.canvas.flush_events()
            time.sleep(common.const.GUI_UPDATE_TIME)

    @staticmethod
    def _define_ampl_plot(pyplot, indices):
        pyplot.subplot(3, 1, 1)
        pyplot.title('Combined Amplitude')
        pyplot.xticks(np.arange(0, len(indices), len(indices) // 10))
        ax = pyplot.gca()
        ax.set_xlim(0, len(indices) - 1)
        lines = ax.plot(indices, indices, 'k-',
                        linewidth = 0.5)
        return (ax, lines)

    @staticmethod
    def _define_trigger_function_plot(pyplot, indices):
        pyplot.subplot(3, 1, 2)
        pyplot.title('Trigger Function')
        pyplot.xticks(np.arange(0, len(indices), len(indices) // 10))
        ax = pyplot.gca()
        ax.set_xlim(0, len(indices) - 1)
        lines = ax.plot(indices, indices, 'k-',
                        linewidth = 0.5)
        return (ax, lines)

    @staticmethod
    def _define_zoom_plot(pyplot, indices):
        pyplot.subplot(3, 1, 3)
        pyplot.title('Zoom Centered on Trigger Point')
        pyplot.xticks(np.arange(0, pinger.const.L_TRIGGER_ZOOM_PLOT,
            pinger.const.L_TRIGGER_ZOOM_PLOT // 10))
        ax = pyplot.gca()
        ax.set_xlim(0, pinger.const.L_TRIGGER_ZOOM_PLOT - 1)
        lines = ax.plot(indices, indices, 'r-',
                        indices, indices, 'g-',
                        indices, indices, 'b-',
                        indices, indices, 'm-',
                        linewidth = 0.5)
        return (ax, lines)

