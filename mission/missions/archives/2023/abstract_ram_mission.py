
from mission.framework.base import AsyncBase
from mission.framework.movement import *

from mission.framework.primitive import *
from mission.framework.contexts import *

from math import exp, cos, sin, tan, pi, radians
from typing import Callable

from asyncio import sleep

LARGE_TOLERANCE = 2.0 ** 32.0 

DEFAULT_DISTANCE = 10.0 # Meters
PRINT_DEBUG_INFO = True

class AbstractRamMission(AsyncBase):

    def __init__(self, 
                period: float, # amount of time between loops
                done_condition: Callable[[], bool], # condition that marks the end of the ram mission
                max_forward_speed: float, # speed sub will move once aligned
                max_angle_error: float, # maximum error allowed before beginning to ram
                is_visible: Callable[[], bool], # if object you wish to ram is visible
                yaw_provider: Callable[[], float], # yaw from +x towards object you want to ram
                pitch_provider: Callable[[], float], # pitch from +x towards object you want to ram
                distance_provider: Callable[[], float]=lambda: DEFAULT_DISTANCE # estimated distance to object
            ):
        self._period = period
        self._is_done = done_condition

        self._max_speed = max_forward_speed
        self._max_error = max_angle_error

        self._is_visible = is_visible
        self._yaw = yaw_provider
        self._pit = pitch_provider
        self._dist = distance_provider

        self._previous_data = (None, None, None)

        self.first_task = self.main()

    async def main(self):
        while not self._is_done():
        
            # fetch data from providers
            data = (self._yaw(), self._pit(), self._dist())

            if not self._is_visible():
                print('\n'.join((
                    f"",
                    f"",
                    f"Abstract Ram Mission:",
                    f"    - Warning: Unable to see object!"
                    )))

                await zero()


            # determine if data is fresh
            elif data != self._previous_data:
                self._previous_data = data
                yaw, pitch, distance = data

                # update internal submarine target yaw, depth, 
                # and speed values inorder to ram object
                with PositionalControls(False):
                    yaw_offset = yaw
                    depth_offset = distance * tan(radians(pitch))
                    
                    speed = self._max_speed * exp(-(yaw * yaw + pitch * pitch) / (self._max_error * self._max_error))

                    yaw_setter = relative_to_initial_heading(yaw_offset, LARGE_TOLERANCE)
                    depth_setter = relative_to_initial_depth(-depth_offset, LARGE_TOLERANCE)
                    speed_setter = velocity_x(speed)

                    await yaw_setter
                    await depth_setter
                    await speed_setter

                    if PRINT_DEBUG_INFO:
                        print('\n'.join((
                        f"",
                        f"",
                        f"Abstract Ram Mission:",
                        f"    - Readings:",
                        f"        - Yaw ............ {yaw:6.2f} deg",
                        f"        - Pitch .......... {pitch:6.2f} deg",
                        f"        - Distance ....... {distance:6.3f} m",
                        f"    - Outputs:",
                        f"        - Depth Offset ... {depth_offset:6.3f} m",
                        f"        - Speed .......... {speed:6.3f} m/s"
                        )))
                        
            await sleep(self._period)

        if PRINT_DEBUG_INFO:
            print("Abstract Ram Mission: Finished!")
    
        await zero()
