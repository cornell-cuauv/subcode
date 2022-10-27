from typing import Optional, Dict, Any, List
import inspect

import shm
from conf.vehicle import is_minisub

from mission.async_framework.logger import log

class SetterContext:
    """A context manager for holding a SHM variables at a value."""
    initial_values : Dict[Any, Any] = {}
    context_depths : Dict[Any, int] = {}

    def __init__(self, value, shm_var):
        self.value = value
        self.shm_var = shm_var

    def __enter__(self):
        if self.value is not None:
            if self.shm_var not in SetterContext.initial_values:
                SetterContext.initial_values[self.shm_var] = self.shm_var.get()
                SetterContext.context_depths[self.shm_var] = 1
                self.shm_var.set(self.value)
            elif self.value != self.shm_var.get():
                raise Exception("Attempted SetterContext contradiction for SHM "
                        f"variable {str(self.shm_var)[12:-2]}. Previous value "
                        f"was {self.shm_var.get()}; new value is {self.value}.")
            else:
                SetterContext.context_depths[self.shm_var] += 1

    def __exit__(self, type, value, traceback):
        if self.value is not None:
            SetterContext.context_depths[self.shm_var] -= 1
            if SetterContext.context_depths[self.shm_var] == 0:
                self.shm_var.set(SetterContext.initial_values[self.shm_var])
                del SetterContext.initial_values[self.shm_var]
                del SetterContext.context_depths[self.shm_var]

class PositionalControls(SetterContext):
    """A context manager which holds on or off positional controls.

    The controller can accept desires for the sub's velocity or desires for the
    sub's position, but it cannot work with both simulataneously because they
    will usually contradict one another. (Imagine trying to stay at position
    (0, 0) while simultaneously moving at 0.5 meters per second.)

    The navigation_settings SHM group contains a variable called
    position_controls which tells the controller which set of desires it should
    be heeding. Note that it always heeds the desires which relate to neither
    velocity nor position, such as heading, as well as depth which does not
    count as positional in this context.

    This context manager can (and should) be used to turn on and off positional
    controls. Here is its usage:

    with PositionalControls():
        # some code that uses positional desires

    <or>

    with PositionalControls(False):
        # some code that uses velocity desires

    During the duration of the execution of the code within the with block,
    the position_controls SHM variable will be as you desire. As soon as the
    with block is exited, the SHM variable will be reset to its original value.*

    You could set the position_controls SHM variable directly in your missions,
    but doing so has two main problems which this context manager addresses:

    The first is that you may accidentally run multiple tasks concurrently, one
    of which uses positional desires and one of which uses velocity desires. If
    you set the SHM variable directly, at least one of those tasks will not
    behave correctly (since the controller will be ignoring its desires) and it
    will not be clear to you why. This context manager, on the other hand, will
    alert you to an attempted contradiction.

    The second is that if something goes wrong in your mission, such as an
    exception being thrown (or if you simply fail to account for all execution
    paths), positional controls may be left on (or off) without that being your
    intention. This context manager guarantees that the position_controls SHM
    variable will be unset as soon as the with block is exited (no matter how it
    is exited).

    But both of these advantages are only realized if position_controls is
    exclusively set using this context manager around the stack. Please use it
    to spare everyone's sanity.

    Further reading:
    Find the controller in the /control directory.
    Learn moreabout positional controls at https://wiki.cuauv.org/en/Software
    /Training-Competition/Gate/Positional-control-and-navigator.
    Learn more about context managers at
    https://realpython.com/python-with-statement.

    * That is, unless a second instance of the context manager was concurrently
    entered while inside the first and has not yet exited. In this case the
    original value will be restored when the final instance is exited.
    """
    def __init__(self, enabled : bool = True):
        self.value = enabled
        self.shm_var = shm.navigation_settings.position_controls

    def __enter__(self):
        if is_minisub and self.value == True:
            log("Warning: Turning on positional controls on minisub will have "
                    "no effect.", detail="Something is probably wrong.",
                    level="warning")
        super().__enter__()

class OptimizeControls(SetterContext):
    """A context manager which holds on or off control optimization.

    When optimize is enabled, the controller uses spline curves to navigate more
    efficiently (and fancifully) from point to point along a path. But since we
    do not generally have enough information to feed the controller a series of
    points ahead of time, this option is not really used.
    """
    def __init__(self, enabled : bool = True):
        self.value = enabled
        self.shm_var = shm.navigation_settings.optimize

class MaxSpeed:
    """A context manager which holds the sub below a maximum speed.

    If multiple instances of this context manager are entered concurrently, the
    lowest of their specified maximum speeds will be held.
    """
    initial_max: float = float("inf")
    maxes: List[float] = []

    def __init__(self, max_speed : float):
        self.max_speed = max_speed

    def __enter__(self):
        if len(self.maxes) == 0:
            self.initial_max = shm.navigation_settings.max_speed.get()
        self.maxes.append(self.max_speed)
        shm.navigation_settings.max_speed.set(min(self.maxes))

    def __exit__(self):
        self.maxes.remove(self.max_speed)
        if len(self.maxes) > 0:
            shm.navigation_settings.max_speed.set(min(self.maxes))
        else:
            shm.navigation_settings.max_speed.set(self.initial_max) 
