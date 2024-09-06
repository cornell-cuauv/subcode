"""In my opinion, this file is not quite up to spec style-wise. I will remedy
this shortly."""

import shm
import time
import asyncio 

from typing import Any, Tuple, Callable
from dataclasses import dataclass, field

from control.pid import DynamicPID
from mission.framework.primitive import zero
from mission.framework.contexts import PositionalControls
from mission.combinator_framework.helpers import within_deadband
from mission.constants.sub import PidVal

def clamp(a, lo, hi):
    return min(max(a, lo), hi)

def clamped_depth(delta, lo, hi):
    current = shm.kalman.depth.get()
    final   = clamp(current + delta, lo, hi)
    shm.navigation_desires.depth.set(final)

def clamped_heading(delta, lo, hi):
    current = shm.kalman.heading.get()
    final   = clamp((current + delta) % 360, lo, hi)
    shm.navigation_desires.heading.set(final)

def clamped_vx(delta, lo, hi):
    final = clamp(delta, lo, hi)
    shm.navigation_desires.speed.set(final)

def clamped_vy(delta, lo, hi):
    final = clamp(delta, lo, hi)
    shm.navigation_desires.sway_speed.set(final)

@dataclass
class ConsistencyPidLoop:
    output_function : Callable[[float, float, float], None]
    p               : float
    i               : float
    d               : float
    min_output      : float
    max_output      : float
    finished        : Callable[[], bool]
    modulo_error    : bool      = False
    negate          : bool      = False

    _hold_start     : float     = field(init = False, default_factory=time.time)
    _within_target  : bool      = field(init = False, default=False)
    _is_done        : bool      = field(init = False, default=False)
    _pid            : DynamicPID= field(init = False, default_factory=DynamicPID)

    def tick(self, current : float,  desire : float):
        pid_output = self._pid.tick(value=current, desired=desire, p=self.p, i=self.i, d=self.d)
        pid_output = -pid_output if self.negate else pid_output
        self.output_function(pid_output, self.min_output, self.max_output)

@dataclass
class PidLoop:
    output_function : Callable[[float, float, float], None]
    tolerance       : float
    p               : float
    i               : float
    d               : float
    min_output      : float
    max_output      : float
    hold_time       : float
    modulo_error    : bool      = False
    negate          : bool      = False

    _hold_start     : float     = field(init = False, default_factory=time.time)
    _within_target  : bool      = field(init = False, default=False)
    _is_done        : bool      = field(init = False, default=False)
    _pid            : DynamicPID= field(init = False, default_factory=DynamicPID)

    def tick(self, current : float,  desire : float):
        pid_output = self._pid.tick(value=current, desired=desire, p=self.p, i=self.i, d=self.d)

        pid_output = -pid_output if self.negate else pid_output
        self.output_function(pid_output, self.min_output, self.max_output)
        
        result = within_deadband(current, desire, self.tolerance, self.modulo_error)
        if not self._within_target and result:
            self._hold_start = time.time()
            self._within_target = True
        elif not result:
            self._within_target = False

    def finished(self) -> bool:
        return self._within_target and time.time() - self._hold_start >= self.hold_time

async def forward_target(
        point       : Callable[[], Tuple[float,float]], 
        target      : Tuple[float, float], 
        visible     : Callable[[], bool],
        tolerance   : Tuple[float,float]    = (0.03, 0.03),
        hold_time   : float                 = 1,
        limits_y    : Tuple[float, float]   = (-float('inf'), float('inf')),
        limits_z    : Tuple[float, float]   = (0            , float('inf')),
        final_zero  : bool                  = True,
        py          : float                 = PidVal.PY,
        iy          : float                 = PidVal.IY,
        dy          : float                 = PidVal.DY,    
        pz          : float                 = PidVal.PZ,
        iz          : float                 = PidVal.IZ,
        dz          : float                 = PidVal.DZ):
    return await _wait_for_finish(
        forward_target_scary(point, target, tolerance, hold_time, limits_y, limits_z, 
            py, iy, dy, pz, iz, dz), visible, final_zero)

async def forward_target_scary(
        point       : Callable[[], Tuple[float,float]], 
        target      : Tuple[float, float], 
        tolerance   : Tuple[float,float]    = (0.03, 0.03),
        hold_time   : float                 = 1,
        limits_y    : Tuple[float, float]   = (-float('inf'), float('inf')),
        limits_z    : Tuple[float, float]   = (0            , float('inf')),
        py          : float                 = PidVal.PY,
        iy          : float                 = PidVal.IY,
        dy          : float                 = PidVal.DY,    
        pz          : float                 = PidVal.PZ,
        iz          : float                 = PidVal.IZ,
        dz          : float                 = PidVal.DZ):
    pidy = PidLoop(clamped_vy, tolerance[0], p = py, i = iy, d = dy,
            min_output = limits_y[0], max_output = limits_y[1], hold_time=hold_time, modulo_error = False, 
            negate = True)
    pidz = PidLoop(clamped_depth, tolerance[1], p = pz, i = iz, d = dz,
            min_output = limits_z[0], max_output = limits_z[1], hold_time=hold_time, modulo_error = False,
            negate = True)

    with PositionalControls(False):
        while not (pidy.finished() and pidz.finished()):
            (x,y) = point()
            pidy.tick(x, target[0])
            pidz.tick(y, target[1])
            await asyncio.sleep(0.01)

#returns false if lost visibility, true if succeeds
async def heading_target(
        point       : Callable[[], Tuple[float,float]], 
        target      : Tuple[float, float], 
        visible     : Callable[[], bool],
        tolerance   : Tuple[float,float]    = (0.03, 0.03),
        hold_time   : float                 = 1, 
        limits_h    : Tuple[float, float]   = (-float('inf'), float('inf')),
        limits_z    : Tuple[float, float]   = (0.6          , float('inf')),
        final_zero  : bool                  = True,
        ph          : float                 = PidVal.PH,
        ih          : float                 = PidVal.IH,
        dh          : float                 = PidVal.DH,    
        pz          : float                 = PidVal.PZ,
        iz          : float                 = PidVal.IZ,
        dz          : float                 = PidVal.DZ):
    return await _wait_for_finish(
        heading_target_scary(point, target, tolerance, hold_time, limits_h, limits_z,
            ph, ih, dh, pz, iz, dz), visible, final_zero)

async def heading_target_scary(
        point       : Callable[[], Tuple[float,float]], 
        target      : Tuple[float, float], 
        tolerance   : Tuple[float,float]    = (0.03, 0.03),
        hold_time   : float                 = 1, 
        limits_h    : Tuple[float, float]   = (-float('inf'), float('inf')),
        limits_z    : Tuple[float, float]   = (0.6          , float('inf')),
        ph          : float                 = PidVal.PH,
        ih          : float                 = PidVal.IH,
        dh          : float                 = PidVal.DH,    
        pz          : float                 = PidVal.PZ,
        iz          : float                 = PidVal.IZ,
        dz          : float                 = PidVal.DZ):

    pidh = PidLoop(clamped_heading, tolerance[0], p = ph, i = ih, d = dh,
            min_output = limits_h[0], max_output = limits_h[1], hold_time=hold_time, modulo_error = True, 
            negate = True)
    pidz = PidLoop(clamped_depth, tolerance[1], p = pz, i = iz, d = dz,
            min_output = limits_z[0], max_output = limits_z[1], hold_time=hold_time, modulo_error = False,
            negate = True)

    with PositionalControls(False):
        while not (pidh.finished() and pidz.finished()):
            (x,y) = point()
            pidh.tick(x, target[0])
            pidz.tick(y, target[1])
            await asyncio.sleep(0.01)

async def downward_target(
        point       : Callable[[], Tuple[float,float]], 
        target      : Tuple[float, float], 
        visible     : Callable[[], bool],
        tolerance   : Tuple[float,float]    = (0.03, 0.03),
        hold_time   : float                 = 1, 
        limits_x    : Tuple[float, float]   = (-float('inf'), float('inf')),
        limits_y    : Tuple[float, float]   = (-float('inf'), float('inf')),
        final_zero  : bool                  = True,
        px          : float                 = PidVal.PX,
        ix          : float                 = PidVal.IX,
        dx          : float                 = PidVal.DX,    
        py          : float                 = PidVal.PY,
        iy          : float                 = PidVal.IY,
        dy          : float                 = PidVal.DY):

    return await _wait_for_finish(
        downward_target_scary(point, target, tolerance, hold_time, limits_x, limits_y,
            px, ix, dx, py, iy, dy), visible, final_zero)

async def downward_target_scary(
        point       : Callable[[], Tuple[float,float]], 
        target      : Tuple[float, float], 
        tolerance   : Tuple[float,float]    = (0.03, 0.03),
        hold_time   : float                 = 1, 
        limits_x    : Tuple[float, float]   = (-float('inf'), float('inf')),
        limits_y    : Tuple[float, float]   = (-float('inf'), float('inf')),
        px          : float                 = PidVal.PX,
        ix          : float                 = PidVal.IX,
        dx          : float                 = PidVal.DX,    
        py          : float                 = PidVal.PY,
        iy          : float                 = PidVal.IY,
        dy          : float                 = PidVal.DY):
    # Camera X axis is Sub Y axis
    # The "Untangling" is done here so for the user, x deals with forward/backward 
    #   and y deals with left/right
    pidx = PidLoop(clamped_vy, tolerance[0], p = py, i = iy, d = dy,
            min_output = limits_y[0], max_output = limits_y[1], hold_time=hold_time, modulo_error = False,
            negate = True)
    pidy = PidLoop(clamped_vx, tolerance[1], p = px, i = ix, d = dx,
            min_output = limits_x[0], max_output = limits_x[1], hold_time=hold_time, modulo_error = False, 
            negate = False)

    with PositionalControls(False):
        while not (pidx.finished() and pidy.finished()):
            (x,y) = point()
            pidx.tick(x, target[0])
            pidy.tick(y, target[1])
            await asyncio.sleep(0.01)

async def downward_align(
        angle       : Callable[[], float],
        target      : float,
        visible     : Callable[[], bool],
        tolerance   : float                 = 1,
        hold_time   : float                 = 1,
        limits      : Tuple[float, float]   = (-float('inf'), float('inf')),
        final_zero  : bool                  = True
    ):
    return await _wait_for_finish(downward_align_scary(angle, target, tolerance,
            hold_time, limits), visible, final_zero)

async def downward_align_scary(
        angle       : Callable[[], float],
        target      : float                 = 0,
        tolerance   : float                 = 0.05,
        hold_time   : float                 = 1,
        limits      : Tuple[float, float]   = (-float('inf'), float('inf'))
    ):
    # there really isn't a need for a PID loop if you already know you current and desired angle. 
    # but I also don't want to change the code
    # thus a p value of 1 accomplishes the same thing lol
    pid = PidLoop(clamped_heading, tolerance, p=1, i=0, d=0,
            min_output=limits[0], max_output=limits[1], hold_time=hold_time,
            modulo_error=True, negate=True)

    with PositionalControls(False):
        while not pid.finished():
            pid.tick(angle(), target)
            await asyncio.sleep(0.01)

async def downward_approach(
        size       : Callable[[], float],
        target      : float,
        visible     : Callable[[], bool],
        tolerance   : float                 = 0.001,
        hold_time   : float                 = 1,
        limits      : Tuple[float, float]   = (0.6, float('inf')),
        final_zero  : bool                  = True,
        p           : float                 = PidVal.PA,
        i           : float                 = PidVal.IA,
        d           : float                 = PidVal.DA):
    return await _wait_for_finish(downward_approach_scary(size, target, tolerance,
            hold_time, limits, p, i, d), visible, final_zero)

async def downward_approach_scary(
        size        : Callable[[], float],
        target      : float                 = 0,
        tolerance   : float                 = 0.001,
        hold_time   : float                 = 1,
        limits      : Tuple[float, float]   = (0.6, float('inf')),
        p           : float                 = PidVal.PA,
        i           : float                 = PidVal.IA,
        d           : float                 = PidVal.DA):

    pid = PidLoop(clamped_depth, tolerance, p=p, i=i, d=d, 
            min_output = limits[0], max_output = limits[1], hold_time=hold_time,
            modulo_error=False, negate=False)

    with PositionalControls(False):
        while not pid.finished():
            pid.tick(size(), target)
            await asyncio.sleep(0.01)

"""
async def consistency_forward_align(
        angle       : Callable[[], float],
        target      : float,
        visible     : Callable[[], bool],
        finished    : Callable[[], bool],
        limits      : Tuple[float, float]   = (-float('inf'), float('inf')),
        p           : float                 = PidVal.PH,
        i           : float                 = PidVal.IH,
        d           : float                 = PidVal.DH):
        #Uses "rectangularity" instead of angle
    return await _wait_for_finish(consistency_forward_align_scary(angle, finished,
            target, limits, p, i, d), visible)

async def consistency_forward_align_scary(
        angle       : Callable[[], float],
        finished    : Callable[[], bool],
        target      : float                 = 0,
        limits      : Tuple[float, float]   = (-float('inf'), float('inf')),
        p           : float                 = PidVal.PH,
        i           : float                 = PidVal.IH,
        d           : float                 = PidVal.DH):
    pid = ConsistencyPidLoop(clamped_heading, tolerance, p=p, i=i, d=d,
            min_output=limits[0], max_output=limits[1], finished=finished,
            modulo_error=True, negate=True)
    while not pid.finished():
        pid.tick(angle(), target)
        await asyncio.sleep(0.01)
"""

async def forward_align(
        angle       : Callable[[], float], #point on camera
        target      : float, #point we are aligning to
        visible     : Callable[[], bool],
        tolerance   : float                 = 0.05,
        hold_time   : float                 = 1,
        limits      : Tuple[float, float]   = (-float('inf'), float('inf')),
        final_zero  : bool                  = True,
        p           : float                 = PidVal.PH,
        i           : float                 = PidVal.IH,
        d           : float                 = PidVal.DH):
        #Uses "rectangularity" instead of angle
    return await _wait_for_finish(forward_align_scary(angle, target, tolerance,
            hold_time, limits, p, i, d), visible)

async def forward_align_scary(
        angle       : Callable[[], float],
        target      : float                 = 0,
        tolerance   : float                 = 0.05,
        hold_time   : float                 = 1,
        limits      : Tuple[float, float]   = (-float('inf'), float('inf')),
        p           : float                 = PidVal.PH,
        i           : float                 = PidVal.IH,
        d           : float                 = PidVal.DH):
    pid = PidLoop(clamped_heading, tolerance, p=p, i=i, d=d,
            min_output=limits[0], max_output=limits[1], hold_time=hold_time,
            modulo_error=True, negate=True)
    while not pid.finished():
        pid.tick(angle(), target)
        await asyncio.sleep(0.01)



async def _wait_for_finish(targetting_task: Any, visible: Callable[[], bool],
        final_zero : bool):
    future = asyncio.create_task(targetting_task)
    try:
        while not future.done():
            if not visible():
                print('not visible')
                future.cancel()
                await asyncio.sleep(0)
                await zero()
                return False
            await asyncio.sleep(0.05)
    except asyncio.CancelledError:
        future.cancel()
        await asyncio.sleep(0)
        raise
    if final_zero:
        await zero()
    return True
 
