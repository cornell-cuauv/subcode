#!/usr/bin/env python3
import time
import shm

from conf.vehicle import cameras

from vision.modules.base import ModuleBase, _PsuedoOptionsDict
from vision import options

directions = cameras.keys()

o = [
        ("double", "{}_blue_gain", 0.0, 50.0),
        ("double", "{}_exposure", 0.0, 50.0),
        ("double", "{}_green_gain", 0.0, 50.0),
        ("double", "{}_red_gain", 0.0, 50.0),
        ]

opts = []

for t in o:
    for d in directions:
        if t[0] == "double":
            var = t[1].format(d)
            opts.append(options.DoubleOption(var, getattr(shm.camera, var).get(), t[2], t[3]))
        elif t[0] == "int":
            var = t[1].format(d)
            opts.append(options.IntOption(var, getattr(shm.camera, var).get(), t[2], t[3]))


class Calibrate(ModuleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process(self, *mats):
        for t in o:
            for d in directions:
                var = t[1].format(d)
                getattr(shm.camera, var).set(self.options[var])
        for i, m in enumerate(mats):
            self.post(directions[i], m)


if __name__ == '__main__':
    Calibrate(directions, opts)()
