#!/usr/bin/env python3

from vision.modules.base import ModuleBase
from vision import options
from vision.framework.color import thresh_color_distance, bgr_to_lab
from vision.framework.feature import outer_contours

module_options = [
    options.IntOption('l', 100, 0, 255),
    options.IntOption('a', 160, 0, 255),
    options.IntOption('b', 150, 0, 255),
    options.IntOption('dist', 20, 0, 25),
]

class AaronTest(ModuleBase):
    def process(self, img):
        _, lab = bgr_to_lab(img)
        threshed, _ = thresh_color_distance(lab, (self.options['l'],
                self.options['a'], self.options['b']), self.options['dist'])
        self.post('threshed', threshed)
        contours = outer_contours(threshed)
        


if __name__ == '__main__':
    AaronTest('forward', module_options)()