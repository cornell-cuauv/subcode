import tomlkit
import numpy as np
import os
import sys
from typing import Union, Any, Dict
from tomlkit.container import Container

from tomlkit.items import Item, Array

DIR = os.environ.get("CUAUV_SOFTWARE")
if DIR is None:
    sys.stderr.write("vehicle.py: CUAUV_SOFTWARE must be set "
                     "to the root of the software repository.\n")
    sys.exit(1)

d = None
VEHICLE = os.getenv("CUAUV_VEHICLE")
VEHICLE_TYPE = os.getenv("CUAUV_VEHICLE_TYPE")

if VEHICLE is None or not VEHICLE in ["odysseus", "ajax"]:
    sys.stderr.write("vehicle.py: CUAUV_VEHICLE must be set "
                     "to one of { odysseus, ajax }.\n")
    sys.exit(1)
if VEHICLE_TYPE is None or not VEHICLE_TYPE in ["mainsub", "minisub"]:
    sys.stderr.write("vehicle.py: CUAUV_VEHICLE_TYPE must be set "
                     "to one of { mainsub, minisub }.\n")
    sys.exit(1)

is_mainsub = VEHICLE_TYPE == "mainsub"
is_minisub = VEHICLE_TYPE == "minisub"

with open(os.path.join(DIR, "conf", "{}.toml".format(VEHICLE))) as f:
    d = tomlkit.parse(f.read())

#(Nathaniel 2023-03): IMO vehicle should be encapsulated as a class,
#but for now this enables backwards compatability with current way of 
#accessing global variables through importing vehicle.

#dict of global variables in this module
g = globals()

for key in d:
    value = d[key]
    if type(value) is Array:
        value = np.array(value)
    g[key] = value


if os.getenv('CUAUV_LOCALE') == 'simulator':
    dvl_scaling_factor = 1


# note: the inherit from object is needed for Python 2 compatibility
# (it makes it a 'new-style' object, which is the default in Python 3)
class DragPlane(object):
    def __init__(self, pos, normal, cD, area):
        self.pos = pos
        self.n = normal
        self.cD = cD
        self.area = area

        self.torque_hat = np.cross(self.pos, self.n)


# I refuse to type drag planes if we're not using them
drag_planes = []
for dp in d['drag_planes']: # type: ignore
    drag_planes.append(DragPlane(np.array(dp['pos']), np.array(dp['normal']), dp['cD'], dp['area'])) # type: ignore


try:
  cameras = d['cameras']
except KeyError:
  print("WARNING: Vehicle %s is missing camera configuration." % VEHICLE)

try:
  vision_modules = d['vision_modules']
except KeyError:
    print("WARNING: Vehicle %s is missing vision module configuration." % VEHICLE)
