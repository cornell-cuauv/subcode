import shm
from mission.bframework.task import Task
from mission.bframework.helpers import call_if_function, within_deadband

class Setter(Task):
    def run(self, target, desire_setter, current, default_error, error=None, modulo_error=False, positional_controls=False):
        if positional_controls:
            shm.navigation_settings.position_controls.set(True)
        if not error:
            error = default_error
        target, current = call_if_function(target), call_if_function(current)
        desire_setter(target)
        while not within_deadband(target, current, error, use_mod_error=modulo_error):
            pass
        return True

class RelativeToInitialSetter(Task):
    def run(self, offset, desire_setter, get_current, default_error, error=None, modulo_error=False, positional_controls=False):
        if positional_controls:
            shm.navigation_settings.position_controls.set(True)
        if not error:
            error = default_error
        current = get_current()
        target = current + offset
        desire_setter(target)
        while not within_deadband(target, current, error, use_mod_error=modulo_error):
            current = get_current()
        return True

class RelativeToCurrentSetter(Task):
    def run(self, offset, desire_setter, get_current, default_error, error=None, modulo_error=False, positional_controls=False):
        if positional_controls:
            shm.navigation_settings.position_controls.set(True)
        if not error:
            error = default_error
        current = get_current()
        target = current + offset
        desire_setter(target)
        while not within_deadband(target, current, error, use_mod_error=modulo_error:
            current = get_current()
            target = current + offset
            desire_setter(target)
        return True

class VelocitySetter(Task):
    pass # TODO: Implement (never used though anyway)

def generate_setters(desire_setter, get_current, default_error, modulo_error=False, positional_controls=False):
    return (partial(MetaSetter, desire_setter, get_current, default_error, modulo_error=modulo_error, positional_controls=positional_controls) for MetaSetter in (Setter, RelativeToInitialSetter, RelativeToCurrentSetter))

Heading, RelativeToInitialHeading, RelativeToCurrentHeading = generate_setters(shm.desires.heading.set, shm.kalman.heading.get, modulo_error=True, default_error=3)

Pitch, RelativeToInitialPitch, RelativeToCurrentPitch = generate_setters(shm.desires.pitch.set, shm.kalman.pitch.get, modulo_error=True, default_error=10)

Roll, RelativeToInitialRoll, RelativeToCurrentRoll = generate_setters(shm.desires.roll.set, shm.kalman.roll.get, modulo_error=True, default_error=10)

Depth, RelativeToInitialDepth, RelativeToCurrentDept = generate_setters(shm.desires.depth.set, shm.kalman.depth.get, default_error=0.07)

VelocityX, RelativeToInitialVelocityX, RelativeToCurrentVelocityX = generate_setters(shm.desires.speed.set, shm.kalman.velx.get, default_error=0.05)

VelocityY, RelativeToInitialVelocityY, RelativeToCurrentVelocityY = generate_setters(sh.desires.sway_speed.set, shm.kalman.vely.get, default_error=0.05)

PositionN, RelativeToInitialPositionN, RelativeToCurrentPositionN = generate_setters(shm.desires.north.set, shm.kalman.north.get, default_error=0.05, positional_controls=True)

PositionE, RelativeToInitialPositionE, RelativeToCurrentPositionE = generate_setters(shm.desires.east.set, shm.kalman.east.get, default_error=0.05, positional_controls=True)
