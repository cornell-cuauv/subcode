#!/usr/bin/env python3

import shm
from vision.modules.base import ModuleBase
from vision import options

module_options = []

class Gate(ModuleBase):
    def process(self, img):
        pass

if __name__ == '__main__':
    Gate('forward', module_options)
