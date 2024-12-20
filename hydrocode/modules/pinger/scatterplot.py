import math
import queue
import time

import matplotlib
from matplotlib import pyplot
from matplotlib.ticker import AutoMinorLocator
import numpy as np

from hydrocode.modules.common import const, plot

class ScatterPlot(plot.PlotBase):
    """This plot shows the tracking precision if the sub is held fixed.

    Plot updates on every ping processing interval. New points are
    progressively added for each tracked ping in a 2D graph with
    heading on the x-axis and elevation on the y-axis. Plot also shows
    an updating mean and standard deviation for both angles.
    """

    def plot(self, hdg, elev):
        """Add a new datapoint.

        :param hdg: heading (rad)
        :param elev: elevation (rad)
        """

        try:
            self._q.put_nowait((hdg, elev))
        except queue.Full:
            pass

    @staticmethod
    def _daemon(q):
        matplotlib.use('TkAgg') # only backend that works on macOS
        pyplot.ioff()
        fig = pyplot.figure(figsize=(5, 5))

        pyplot.suptitle('Relative Heading/Elevation Scatter Plot')
        (ax, points, text) = ScatterPlot._define_plot(fig, AutoMinorLocator)

        hdg_list = []
        elev_list = []
        while True:
            try:
                (hdg, elev) = q.get_nowait()
                hdg_list.append(hdg)
                elev_list.append(elev)

                points.set_data(hdg_list, elev_list)
                text.set_text(
                    'HDG std: ' + '{:.2f}'.format(np.std(hdg_list)) + '\n' +
                    'HDG mean: ' + '{:.2f}'.format(np.mean(hdg_list)) + '\n' +
                    'ELEV std: ' + '{:.2f}'.format(np.std(elev_list)) + '\n' +
                    'ELEV mean: ' + '{:.2f}'.format(np.mean(elev_list)))

                pyplot.draw()
                pyplot.show(block=False)
            except queue.Empty:
                pass

            fig.canvas.flush_events()
            time.sleep(const.GUI_UPDATE_TIME)

    @staticmethod
    def _define_plot(fig, AutoMinorLocator):
        # Scatter plot with visible grid. X-axis limits fixed to
        # [-pi, pi], y-axis limits fixed to [-pi / 2, pi / 2].

        ax = fig.add_subplot(111)
        ax.set_xlabel('Heading (rad)')
        ax.set_ylabel('Elevation (rad)')
        ax.set_xticks([-3, -2, -1, 0, 1, 2, 3])
        ax.set_yticks([-1, 0, 1])
        ax.xaxis.set_minor_locator(AutoMinorLocator(10))
        ax.yaxis.set_minor_locator(AutoMinorLocator(10))
        ax.set_xlim(-math.pi, math.pi)
        ax.set_ylim(-math.pi / 2, math.pi / 2)
        ax.set_aspect('equal', adjustable='box')
        ax.grid(True, which='major', linestyle='-')
        ax.grid(True, which='minor', linestyle=':')
        points = ax.plot([], [], color='r', marker='.', ls='', markersize=1)
        text = ax.text(-3, 1.6, '')
        return (ax, points[0], text)