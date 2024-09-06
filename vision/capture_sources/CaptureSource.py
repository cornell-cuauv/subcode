import atexit
import signal
import sys
import time
import threading

from vision import camera_message_framework

from auvlog.client import log as auvlog

# Base class for a capture source. This should never be directly created, but
# instead should be subclassed


class CaptureSource(object):
    # initialize a capture source in the specified {direction}
    # if {persistent} is True, then the capture source will poll the subclass
    #   using the acquire_next_image method for frames to send, at a max rate
    #   of {fps} frames per second
    # if {persistent} is False, the subclass must take care of sending images
    #   itself
    def __init__(self, direction, fps=10.0, persistent=True):
        self._shm = None
        self.fps = fps
        self.direction = direction
        self._persistent = persistent
        logger = auvlog.vision.capture_source
        logger = getattr(logger, self.__class__.__name__)
        self.logger = getattr(logger, direction)
        self._framework = {}

    def acquisition_loop(self):
        running_slow = False
        while self._persistent:
            start_time = time.time()
            next_image, acq_time = self.acquire_next_image()
            if next_image is not None:
                self._send(acq_time, next_image)
            elapsed_time = time.time() - start_time

            if self.fps <= 0:
                continue

            time_to_sleep = 1. / self.fps - elapsed_time

            if time_to_sleep > 0:
                if running_slow:
                    running_slow = False
                    self.logger.log(
                        'Capture source is back to running normally')

                time.sleep(time_to_sleep)
            else:
                if not running_slow:
                    running_slow = True
                    self.logger.warning(
                        'Capture source is running slow: took {} seconds to acquire an image'.format(elapsed_time))

    def acquire_next_image(self):
        assert not self.persistent, 'Persistent CaptureSources must define acquire_next_image'

    def _send(self, acq_time, image, direction=None):
        if direction is None:
            direction = self.direction

        if direction not in self._framework:
            height, width, depth = image.shape
            self._framework[direction] = camera_message_framework.Creator(direction,
                                                                          width*height*depth)

            if not self._framework[direction].valid():
                self._framework[direction].cleanup()
                sys.exit(1)

            def sigh(sig, frame):
                sys.exit(0)

            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGTERM, sigh)

            atexit.register(self._framework[direction].cleanup)
        self._framework[direction].write_frame(image, acq_time)
