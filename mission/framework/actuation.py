import asyncio
from shm import actuator_desires, actuator_status

from math import copysign

actuator_list = []

class Actuator:

    ### CONSTANTS ###

    ON_VAL = 0
    OFF_VAL = 1

    MIN_DEG = -230
    MAX_DEG = +230

    MIN_PWM = 0
    MAX_PWM = 255


    ### INITIALIZATION ###

    def __init__(self, id, name=None):
        self.id = id
        self.name = name if name is not None else f'Actuator #{id}'
        self._on = getattr(actuator_desires, f'act_{id}_on')
        self._pwm = getattr(actuator_desires, f'act_{id}_pwm')
        self._on_readback = getattr(actuator_status, f'act_{id}_on_readback')
        self._pwm_readback = getattr(actuator_status, f'act_{id}_pwm_readback')

        global actuator_list
        actuator_list.append(self)
        actuator_list.sort(key=lambda a: a.id)


    ### ENABLING/DISABLING ###

    def enable(self):
        self._on.set(Actuator.ON_VAL)

    def disable(self):
        self._on.set(Actuator.OFF_VAL)

    def toggle(self):
        if self._on.get() == Actuator.OFF_VAL:
            self._on.set(Actuator.ON_VAL)
        else:
            self._on.set(Actuator.OFF_VAL)

    def get_on(self):
        return self._on.get() == Actuator.ON_VAL
    
    ### SETTING PWM ###

    def set_pwm(self, pwm):
        if pwm < Actuator.MIN_PWM:
            pwm = Actuator.MIN_PWM
        
        if pwm > Actuator.MAX_PWM:
            pwm = Actuator.MAX_PWM
            
        self._pwm.set(int(pwm))

    def set_angle(self, angle):
        angle -= Actuator.MIN_DEG
        angle /= Actuator.MAX_DEG - Actuator.MIN_DEG
        angle *= Actuator.MAX_PWM - Actuator.MIN_PWM
        angle += Actuator.MIN_PWM
        self.set_pwm(angle)
    
    def add_pwm(self, delta):
        self.set_pwm(self.get_pwm() + delta)
        
    def add_angle(self, delta):
        self.set_angle(self.get_angle() + delta)
    
    def get_pwm(self):
        return self._pwm.get()
    
    def get_angle(self):
        pwm = self.get_pwm()
        pwm -= Actuator.MIN_PWM
        pwm /= Actuator.MAX_PWM - Actuator.MIN_PWM
        pwm *= Actuator.MAX_DEG - Actuator.MIN_DEG
        pwm += Actuator.MIN_DEG
        return pwm
    
    ### READBACKS ###
    def get_on_readback(self):
        return self._on_readback.get() == Actuator.ON_VAL

    def get_pwm_readback(self):
        return self._pwm_readback.get()
    
    def get_angle_readback(self):
        pwm = self.get_pwm_readback()
        pwm -= Actuator.MIN_PWM
        pwm /= Actuator.MAX_PWM - Actuator.MIN_PWM
        pwm *= Actuator.MAX_DEG - Actuator.MIN_DEG
        pwm += Actuator.MIN_DEG
        return pwm

    ### PRINTING ###
    def __str__(self):
        return f'{self.id:x}: {self.name}'


manipulator_act = Actuator(0, 'Manipulator')
torpedo_dropper_act = Actuator(1, 'Torpedo & Dropper')
dummy1_act = Actuator(2, 'Unplugged')
dummy2_act = Actuator(3, 'Unplugged')

class TorpedoDropper:
    
    TOLERANCE = 4
    
    TORPEDO_ANGLES = [-72, -144]
    DROPPER_ANGLES = [72, 144]

    NEUTRAL_ANGLE = 0.0
    
    TORPEDO_COUNT = len(TORPEDO_ANGLES)
    DROPPER_COUNT = len(DROPPER_ANGLES)
    
    SHOOT_TIME = 4.0
    
    def __init__(self, actuator):
        self.actuator = actuator
        
        self.torpedos_fired = 0
        self.droppers_fired = 0
    
    async def set_angle(self, angle):
        self.actuator.set_angle(TorpedoDropper.NEUTRAL_ANGLE + angle)

    async def neutral(self):
        self.actuator.enable()
        await self.set_angle(0)
        
    async def reset(self):
        await self.neutral()
        self.torpedos_fired = 0
        self.droppers_fired = 0
        
    async def fire_torpedo(self):
        angle = TorpedoDropper.TORPEDO_ANGLES[self.torpedos_fired]
        angle += copysign(TorpedoDropper.TOLERANCE, angle)
        
        if self.torpedos_fired < TorpedoDropper.TORPEDO_COUNT - 1:
            self.torpedos_fired += 1
        
        self.actuator.enable()
        await self.set_angle(angle)
        await asyncio.sleep(TorpedoDropper.SHOOT_TIME)
        await self.neutral()
        
    async def fire_dropper(self):
        angle = TorpedoDropper.DROPPER_ANGLES[self.droppers_fired]
        angle += copysign(TorpedoDropper.TOLERANCE, angle)

        if self.droppers_fired < TorpedoDropper.DROPPER_COUNT - 1:
            self.droppers_fired += 1
        
        self.actuator.enable()
        await self.set_angle(angle)
        await asyncio.sleep(TorpedoDropper.SHOOT_TIME)
        await self.neutral()
        
torpedo_dropper = TorpedoDropper(torpedo_dropper_act)

async def fire_torpedo():
    await torpedo_dropper.fire_torpedo()
    
async def fire_dropper():
    await torpedo_dropper.fire_dropper()
    
async def reset_torpedo_dropper():
    await torpedo_dropper.reset()

### DEPRECATED OLD FUNCTIONS ###

async def fire_left_torpedo():
    print("WARNING: This function is for an old submarine!")

async def fire_right_torpedo():
    print("WARNING: This function is for an old submarine!")
    
async def release_markers():
    print("WARNING: This function is for an old submarine!")