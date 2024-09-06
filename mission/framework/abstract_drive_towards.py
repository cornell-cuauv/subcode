
from mission.framework.base import AsyncBase
from mission.framework.movement import *

from mission.framework.primitive import *
from mission.framework.contexts import *

from math import exp, cos, sin, tan, pi, radians
from typing import Callable

from mission.framework.low_pass_filter import LowPassFilter

from asyncio import sleep

LARGE_TOLERANCE = 2.0 ** 32.0 

DEFAULT_DISTANCE = 10.0 # Meters
PRINT_DEBUG_INFO = True

class AbstractDriveTowardsMission(AsyncBase):

    def __init__(self, 
                period: float, # amount of time between loops
                done_condition: Callable[[], bool], # condition that marks the end of the ram mission
                max_forward_speed: float, # speed sub will move once aligned
                max_angle_error: float, # maximum error allowed before beginning to ram
                is_visible: Callable[[], bool], # if object you wish to ram is visible
                yaw_provider: Callable[[], float], # yaw from +x towards object you want to ram
                depth_provider: Callable[[], float], # relative depth of object you want to ram
            ):
        self._period = period
        self._is_done = done_condition

        self._max_speed = max_forward_speed
        self._max_error = max_angle_error

        self._is_visible = is_visible
        self._yaw = yaw_provider
        self._depth = depth_provider

        self._previous_data = (None, None)

        self._speed_filter = LowPassFilter(1.0)

        self.first_task = self.main()

    async def main(self):
        while not self._is_done():
        
            # fetch data from providers
            data = (self._yaw(), self._depth())

            if not self._is_visible():
                print('\n'.join((
                    f"",
                    f"",
                    f"Abstract Drive Towards Mission:",
                    f"    - Warning: Unable to see object!"
                    )))

                with PositionalControls(False):
                    await velocity_x(self._speed_filter.get(0.0), tolerance=LARGE_TOLERANCE)

            # determine if data is fresh
            elif data != self._previous_data:
                self._previous_data = data
                yaw, depth = data

                # update internal submarine target yaw, depth, 
                # and speed values inorder to ram object
                with PositionalControls(False):
                    yaw_offset = yaw
                    
                    speed = self._max_speed * exp(-(yaw * yaw) / (self._max_error * self._max_error))

                    yaw_setter = relative_to_initial_heading(yaw_offset, tolerance=LARGE_TOLERANCE)
                    speed_setter = velocity_x(self._speed_filter.get(speed), tolerance=LARGE_TOLERANCE)

                    if abs(depth) > 0.5:
                        await relative_to_initial_depth(depth, tolerance=LARGE_TOLERANCE)

                    await yaw_setter
                    await speed_setter

                    if PRINT_DEBUG_INFO:
                        print('\n'.join((
                        f"",
                        f"",
                        f"Abstract Drive Towards:",
                        f"    - Readings:",
                        f"        - Yaw ............ {yaw:6.2f} deg",
                        f"        - Depth .......... {depth:6.2f} m",
                        f"    - Outputs:",
                        f"        - Speed .......... {speed:6.3f} m/s"
                        )))
                        
            await sleep(self._period)

        if PRINT_DEBUG_INFO:
            print("Abstract Ram Mission: Finished!")
    
        await zero()
