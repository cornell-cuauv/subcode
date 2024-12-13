#!/usr/bin/env python3
import numpy as np
from vision.core.base import ModuleBase

try:
    from vision.capture_sources.zed import ZED_MIN_DISTANCE, ZED_MAX_DISTANCE
except ImportError:
    ZED_MIN_DISTANCE = 0
    ZED_MAX_DISTANCE = 1


class Poster(ModuleBase):
    def process(self, direction, image):
        if direction == "depth":
            image -= ZED_MIN_DISTANCE
            image /= ZED_MAX_DISTANCE - ZED_MIN_DISTANCE
            image *= 255
            image = np.clip(image, 0, 255).astype(np.uint8)
        elif direction == "normal":
            image = np.clip(image * 255, 0, 255).astype(np.uint8)

        self.post(direction, image)


if __name__ == "__main__":
    Poster(["forward"])()
