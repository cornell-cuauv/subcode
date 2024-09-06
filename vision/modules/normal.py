#!/usr/bin/env python3
from vision.modules.base import ModuleBase
from vision import options
from vision.framework.transform import decode_normal
from vision.framework.draw import draw_circle
import cv2
import math

module_options = [
    options.IntOption('x', 400, 0, 720),
    options.IntOption('y', 400, 0, 1280),
]

class Normal(ModuleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = self.y = self.z = 0
        self.count = 0
    
    def reset(self):
        self.x = self.y = self.z = self.count = 0

    def process(self, img):
        img_transformed = decode_normal(img)

        coord_x, coord_y = self.options['x'], self.options['y']

        x, y, z = img_transformed[coord_x, coord_y]
    
        # Keep a moving average of x, y, z 
        self.count += 1
        self.x = ((self.x * (self.count - 1)) + x) / self.count
        self.y = ((self.y * (self.count - 1)) + y) / self.count
        self.z = ((self.z * (self.count - 1)) + z) / self.count
        print(self.x, self.y, self.z)
        print(img[coord_x, coord_y])

        draw_circle(img, (coord_y, coord_x), 10, thickness=10)
        self.post("point", img)


if __name__ == '__main__':
    Normal("normal", module_options)()