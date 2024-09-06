import math

from hydrocode.modules.common import const
from hydrocode.modules.pinger import headingplot, scatterplot

class AnglesMLE:
    """Obtains relative heading/elevation angles from phase differences.

    Under the assumption that phase noise is gaussian, this algorithm is
    the maximum likelihood estimator. Works both for the 3 hydrophone
    and for the 4 hydrophone cases. Math is shown in the Pinger Tracking
    DSP document.
    """

    def __init__(self, heading_plot=False, scatter_plot=False):
        """Constructor.

        :param heading_plot: True to produce heading plot, defaults to
            False
        :param scatter_plot: True to produce scatter plot, defaults to
            False
        """

        self._heading_plot = (
            headingplot.HeadingPlot() if heading_plot else None)
        self._scatter_plot = (
            scatterplot.ScatterPlot() if scatter_plot else None)

    def hdg_elev(self, ping_phase, w):
        """Get heading and elevation from phase differences.

        Pinger directly ahead -> 0 rad heading.
        Pinger to the right -> pi / 2 rad, to the left -> -pi / 2 rad.

        Pinger at the same level -> 0 rad elevation.
        Pinger directly above -> pi / 2 rad, below -> -pi / 2 rad.

        :param ping_phase: array of three or four phases (rad),
            depending on the USE_4CHS setting
        :param w: normalized angular frequency of the tracked signal
        :return: tuple of the form (heading, elevation) (rad), wrapped
            to [-pi, pi) for heading, [-pi / 2, pi / 2] for elevation.
        """

        d = list(self._path_diff(wrap_angle(ping_phase - ping_phase[0]), w))

        v = math.sqrt(d[1] ** 2 + d[2] ** 2)
        hdg = 0 if v == 0 else math.atan2(d[1], d[2])

        if const.USE_4CHS:
            elev = 0 if v == 0 and d[3] == 0 else -math.atan2(d[3], v)
        else:
            elev = 0 if v > 1 else -math.acos(v)

        hdg += const.ENCLOSURE_OFFSET
        hdg = wrap_angle(hdg)

        if self._heading_plot is not None:
            self._heading_plot.plot(hdg, elev)

        if self._scatter_plot is not None:
            self._scatter_plot.plot(hdg, elev)

        return (hdg, elev)

    @staticmethod
    def _path_diff(ph, w):
        """Get path differences corresponding to a phase differences.

        Result is normalized to the baseline, so range is [-1, 1].

        :param ph: array of phase differences (rad)
        :param w: normalized angular frequency of the tracked signal
        :return: array of path differences
        """

        return const.SOUND_SPEED * ph / (const.NIPPLE_DIST *
            const.SAMPLE_RATE * w)

def wrap_angle(theta):
    """Wrap angles to [-pi, pi).

    :param theta: array of angles to wrap (rad)
    :return: wrapped angles (rad)
    """
    PI = 3.14159265358979323846
    theta = (theta + 3 * PI) % (2 * PI) - PI
    theta = (theta + 3 * PI) % (2 * PI) - PI
    return (theta + 3 * PI) % (2 * PI) - PI
