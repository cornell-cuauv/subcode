import time
import random
import shm
from deadman import deadman

SECTIONS = 10
LEDS_PER_SECTION = 6

def ultimate_debug():
    """
    hardkill -> red
    softkill but not harkill -> yellow
    no internet -> green
    high pressure -> magenta
    low battery -> blue
    """
    while True:
        colors = []
        if shm.switches.hard_kill.get():
            colors.append((255, 0, 0))
        elif shm.switches.soft_kill.get():
            colors.append((255, 255, 0))
        if not deadman.ping(deadman.IP_ADDRESS):
            colors.append((0, 255, 0))
        if shm.pressure.hull.get() > 0.725:
            colors.append((255, 0, 255))
        if shm.merge_status.total_voltage.get() < 14.2:
            colors.append((0, 0, 255))
        if len(colors) == 0:
            colors.append((255, 255, 255))
        for section in range(SECTIONS):
            time.sleep(0.05)
            shm.leds.section.set(section)
            time.sleep(0.05)
            color = colors[section % len(colors)]
            for led in range(LEDS_PER_SECTION):
                getattr(shm.leds, f'pixel_{led}r').set(color[0])
                getattr(shm.leds, f'pixel_{led}g').set(color[1])
                getattr(shm.leds, f'pixel_{led}b').set(color[2])


def general_debug():
    while True:
        if shm.switches.hard_kill.get():
            kill_color = (255, 0, 0)
        elif shm.switches.soft_kill.get():
            kill_color = (255, 255, 0)
        else:
            kill_color = (0, 255, 0)
        if deadman.ping(deadman.IP_ADDRESS):
            internet_color = (255, 255, 255)
        else:
            internet_color = (0, 0, 0)
        if shm.pressure.hull.get() < 0.675:
            pressure_color = (0, 0, 255)
        elif shm.pressure.hull.get() < 0.725:
            pressure_color = (255, 0, 255)
        else:
            pressure_color = (255, 128, 0)
        for section in range(SECTIONS):
            color = [kill_color, internet_color, pressure_color][section % 3]
            time.sleep(0.05)
            shm.leds.section.set(section)
            time.sleep(0.05)
            for led in range(LEDS_PER_SECTION):
                getattr(shm.leds, f'pixel_{led}r').set(color[0])
                getattr(shm.leds, f'pixel_{led}g').set(color[1])
                getattr(shm.leds, f'pixel_{led}b').set(color[2])


def set_all(r, g, b):
    for section in range(SECTIONS):
        shm.leds.section.set(section)
        time.sleep(0.05)
        for led in range(LEDS_PER_SECTION):
            getattr(shm.leds, f'pixel_{led}r').set(r)
            getattr(shm.leds, f'pixel_{led}g').set(g)
            getattr(shm.leds, f'pixel_{led}b').set(b)
        time.sleep(0.05)

def set_all_random():
    for section in range(SECTIONS):
        shm.leds.section.set(section)
        time.sleep(0.05)
        for led in range(LEDS_PER_SECTION):
            getattr(shm.leds, f'pixel_{led}r').set(random.randint(0, 255))
            getattr(shm.leds, f'pixel_{led}g').set(random.randint(0, 255))
            getattr(shm.leds, f'pixel_{led}b').set(random.randint(0, 255))
        time.sleep(0.05)

def track_pressure():
    while True:
        pressure = shm.pressure.hull.get()
        if pressure < 0.675:
            set_all(255, 0, 255)
        elif 0.675 < pressure < 0.725:
            set_all(0, 255, 0)
        elif pressure > 0.725:
            set_all(255, 255 - round(min((pressure - 0.725) * 255 / 0.225, 255)), 0)
