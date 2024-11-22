#!/usr/bin/env python3
from vision.core.base import ModuleBase
from vision.core import options
from vision.utils.draw import draw_text

module_options = [
    options.DoubleOption('text_size', 5.0, 0.0, 20.0),
    options.IntOption('text_thickness', 3, 1, 10)
]

class Hello(ModuleBase):
    def process(self, img):
        draw_text(img, "Hello CUAUV!", (100, 200),
                  self.options["text_size"],
                  color=(255, 255, 255),
                  thickness=self.options["text_thickness"])
        self.post("hello", img)

if __name__ == '__main__':
    Hello("forward", module_options)()