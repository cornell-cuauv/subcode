import shm

from mission.framework.primitive import FunctionTask

def light_show(num):
    shm.leds.light_show.set(num)

def get_decimal_color(color):
    # It might be a name
    if color in colors:
        color = colors[color]
    return struct.pack('f', struct.unpack('i', int(color, 16)))

def leds_color(port, star, aft):
    leds = shm.leds.get()
    leds.port_color = get_decimal_color(port)
    leds.starboard_color = get_decimal_color(star)
    leds.aft_color = get_decimal_color(aft)
    shm.leds.set(leds)

LightShow = lambda num: FunctionTask(lambda: light_show(num))

Leds = lambda port, star, aft: FunctionTask(lambda: leds_color(port, star, aft))
AllLeds = lambda color: Leds(color, color, color)

colors = {
    'black': '000000',
    'red': 'FF0000',
    'green': '00FF00',
    'blue': '0000FF',
    'yellow': 'FFFF00',
    'cyan': '00FFFF',
    'purple': 'FF00FF',
    'white': 'FFFFFF',
    'orange': 'FF8000',
}

TestRed = AllLeds('red')
TestCyan = AllLeds('cyan')
TestOrange = AllLeds('orange')
