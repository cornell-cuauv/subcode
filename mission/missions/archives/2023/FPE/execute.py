from mission.framework.movement import relative_to_initial_heading, velocity_x_for_secs, velocity_y_for_secs, velocity_y
from mission.framework.primitive import zero

# Execute Tasks --------------------


async def ram(object, reference=0):
    while (object.is_visible()):
        await velocity_x_for_secs(0.2, 0.5)
    await velocity_x_for_secs(0.2, reference)
    return True


async def ram_back(object, reference=0):
    await ram(object)
    await velocity_x_for_secs(-0.2, reference)
    return True


async def ram_forward(object, reference=0):
    await ram(object)
    await velocity_x_for_secs(0.2, reference)
    return True


async def go_around(object, reference):
    area = object.area()
    for i in range(4):
        while object.is_visible():
            await velocity_y_for_secs(-0.2, 0.1)
        await zero()
        await relative_to_initial_heading(90)
        while (not object.is_visible()) or object.coordinates()[0] < 0:
            await velocity_y_for_secs(-0.2, 0.1)
        await zero()
        if object.area() > area:    # case 1: closer than anticipated, so back up
            while (object.area() > area):
                await velocity_x_for_secs(-0.1, 0.1)
        else:                       # case 2: farther than anticipated, so get closer
            while (object.area() < area):
                await velocity_x_for_secs(0.1, 0.1)
        await zero()
    return True

async def go_around_square(object, reference):
    """go_around_square: goes around [object] in a square"""

    await relative_to_initial_heading(45)
    for i in range(3):
        await velocity_x_for_secs(2.5, 5)
        await relative_to_initial_heading(-90)
    await velocity_x_for_secs(2.5, 5)
    await relative_to_initial_heading(25)
    await zero()
    return True


async def execute_harness(object, reference):
    return True
