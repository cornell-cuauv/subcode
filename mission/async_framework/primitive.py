import shm

async def zero_without_heading(pitch : bool = True, roll : bool = True) -> bool:
    desires, current = shm.navigation_desires, shm.kalman
    desires.depth.set(current.depth.get())
    desires.north.set(current.north.get())
    desires.east.set(current.east.get())
    desires.pitch.set(0 if pitch else current.pitch.get())
    desires.roll.set(0 if roll else current.roll.get())
    desires.speed.set(0)
    desires.sway_speed.set(0)
    return True

async def zero(pitch : bool = True, roll : bool = True) -> bool:
    shm.navigation_desires.heading.set(shm.kalman.heading.get())
    return await zero_without_heading(pitch, roll)

async def enable_controller() -> bool:
    logi("Enabling controller and all PID loops.")
    control = shm.settings_control
    control.enabled.set(1)
    control.heading_active.set(1)
    control.pitch_active.set(1)
    control.roll_active.set(1)
    control.velx_active.set(1)
    control.vely_active.set(1)
    control.depth_active.set(1)
    return True
    
