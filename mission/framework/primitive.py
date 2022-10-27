import shm
from mission.async_framework.logger import log

async def zero_without_heading(pitch : bool = True, roll : bool = True):
    """Set navigation desires to match current values (except for heading).

    Arguments:
    pitch -- should the pitch desire be set to 0 instead of its current value
    roll  -- should the roll desire be set to 0 instead of its current value
    """
    desires, current = shm.navigation_desires, shm.kalman
    desires.depth.set(current.depth.get())
    desires.north.set(current.north.get())
    desires.east.set(current.east.get())
    desires.pitch.set(0 if pitch else current.pitch.get())
    desires.roll.set(0 if roll else current.roll.get())
    desires.speed.set(0)
    desires.sway_speed.set(0)

async def zero(pitch : bool = True, roll : bool = True):
    """Set navigation desires to match current values so the sub stops moving.

    Arguments:
    pitch -- should the pitch desire be set to 0 instead of its current value
    roll  -- should the roll desire be set to 0 instead of its current value
    """
    shm.navigation_desires.heading.set(shm.kalman.heading.get())
    await zero_without_heading(pitch, roll)

async def enable_controller():
    """Enable the controller and every PID loop."""
    log("Enabling controller and all PID loops.")
    control = shm.settings_control
    control.enabled.set(1)
    control.heading_active.set(1)
    control.pitch_active.set(1)
    control.roll_active.set(1)
    control.velx_active.set(1)
    control.vely_active.set(1)
    control.depth_active.set(1)
    
