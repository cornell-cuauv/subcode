import time

import numpy

from misc.log import with_logging
from vision.core.bindings import camera_message_framework as cmf
import shm

#Maps CAVE representation of cameras to the strings
#used for Posix IPC (the camera names within cave_test).
#This may be useful if these vision names are ever changed.
camera_map = {
    "Forward": "forward",
    "Downward": "downward"
}

@with_logging
class CameraLink:

    # Initialize a camera link with the given frame dimensions
    def __init__(self, name, height=None, width=None, nChannels=None):
        self.name = camera_map[name]
        self.height = height
        self.width = width
        self.nChannels = nChannels

        self.dataSize = self.height * self.width * self.nChannels

        self.currentFrame = 0

        #Init shared memory
        self.framework = cmf.BlockAccessor(self.name, self.dataSize)

        # this is very jank, but cave was written before the cmf overhaul
        # this functionally has the same safety guarantees as before,
        # but using context manager gives MORE safety guarantees.
        self.framework.__enter__() 

        # Set camera dimensions in SHM
        try:
            getattr(shm.camera, self.name + '_height').set(self.height)
            getattr(shm.camera, self.name + '_width').set(self.width)
        except AttributeError:
            # There are no SHM camera dimension variables
            pass

    def send_image(self, frame):
        self.framework.write_frame(int(time.time() * 1000), frame)

    def cleanup(self):
        self.framework.__exit__(None, None, None)
