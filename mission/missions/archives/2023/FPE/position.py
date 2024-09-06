from mission.framework.movement import depth, relative_to_initial_heading, velocity_x_for_secs, velocity_y, relative_to_current_depth
from mission.framework.primitive import zero
from mission.framework.targeting import forward_target, downward_target
from mission.framework.FPE.object import QualGate, Path, CompGate, Glyph

import asyncio

# Position Tasks -------------------

async def center_on_object(object, target=(0, 0)):
    """
    center_on_object: centers on [object] at normalized
    coordinate [target].
    """
    success = False
    if isinstance(object, QualGate) or isinstance(object, CompGate):
        success = await forward_target(object.coordinates, target, visible=lambda: object.consistency_tracker().consistent, tolerance=(0.05, 0.05))
        if success:
            await align_gate(object, target)

    elif isinstance(object, Path):

        success = await downward_target(object.coordinates, target, visible=lambda: object.consistency_tracker().consistent, tolerance=(0.1, 0.1))
        if success:
            await align_path(object, target)

    else:
        success = await forward_target(object.coordinates, target, visible=lambda: object.consistency_tracker().consistent)
    return success


async def align_gate(object, target):  # SUPER SCUFFED CODE
    """
    Additional centering if the object is a gate.
    """
    if (object.left_area() < object.right_area()):
        while (object.left_area() < object.right_area()):
            await relative_to_initial_heading(2)
            if not object.shm.middle_visible.get() == 1:
                while (not object.shm.middle_visible.get() == 1):
                    await velocity_y(-0.1)
                await velocity_y(0)
                await forward_target(object.coordinates, target, visible=object.is_visible)
            await zero()
    else:
        while (object.left_area() > object.right_area()):
            await relative_to_initial_heading(360-2)
            if not object.shm.middle_visible.get() == 1:
                while (not object.shm.middle_visible.get() == 1):
                    await velocity_y(0.1)
                await velocity_y(0)
                await forward_target(object.coordinates, target, visible=object.is_visible)
            await zero()
    await forward_target(object.coordinates, target, visible=object.is_visible)
    pass


async def align_path(object, reference):
    await asyncio.sleep(2)
    init_angle = object.angle()
    while (init_angle > 5 and init_angle < 175):
        print("iterating")
        if (init_angle < 90):
            await relative_to_initial_heading(init_angle)
        else:  # init_angle >= 91
            await relative_to_initial_heading(init_angle-180)
        init_angle = object.angle()
        await downward_target(object.coordinates, (0, 0), visible=object.is_visible, tolerance = (0.10, 0.10))
    return True

async def approach_align_chevron(object, area=(100000)):
    await downward_target(object.coordinates, (0, 0), visible=object.is_visible, tolerance = (0.10, 0.10))
    tracker = object.consistency_tracker()
    while object.area() < area:
        coords = object.coordinates()
        if not tracker.consistent:
            return False
        elif (0.5 - abs(coords[0]) < 0.45 or 0.5 - abs(coords[1]) < 0.4):
            await zero()
            print("-- adjustment")
            success = await downward_target(object.coordinates, target=(0, 0), visible=lambda: tracker.consistent, tolerance=(0.08, 0.08))
            await asyncio.sleep(4)
            if not success:
                return False
        print("iterate")
        await relative_to_current_depth(lambda: 0.1)
    await zero()
    await downward_target(object.coordinates, (0, 0), visible=object.is_visible, tolerance = (0.05, 0.05))
    
    init_angle = object.angle()
    await downward_target(object.coordinates, (0, 0), visible=object.is_visible, tolerance = (0.05, 0.05))
    await relative_to_initial_heading(init_angle)
    await downward_target(object.coordinates, (0, 0), visible=object.is_visible, tolerance = (0.05, 0.05))
      
    return True


async def approach(object, area=(10000)):
    """
    approach: approaches an [object] until the observed
    area of the [object] is [area].

    Invariant: at all times, the object is visible, and
    if the object starts to get close to losing visibility
    it will correct itself with forward_target.

    Requires: the object shm group must have an area
    field that is being recorded.
    """
    tracker = object.consistency_tracker()
    while object.area() < area:
        coords = object.coordinates()
        if not tracker.consistent:
            return False
        elif (0.5 - abs(coords[0]) < 0.2 or 0.5 - abs(coords[1]) < 0.2):
            await zero()
            print("-- adjustment")
            success = await forward_target(object.coordinates, target=(0, 0), visible=lambda: tracker.consistent, tolerance=(0.08, 0.08))
            await asyncio.sleep(4)
            if not success:
                return False
        print("iterate")
        await velocity_x_for_secs(0.2, 0.3)
    await zero()
    print("final")
    if isinstance(object, Glyph):
        coord = (0, 0)
        corner = object.shm.heuristic.get()
        if corner == 1:
            coord = (0.05, 0.05)
        elif corner == 2:
            coord = (-0.05, 0.05)
        elif corner == 3:
            coord = (0.05, -0.05)
        elif corner == 4:
            coord = (-0.05, -0.05)
        await forward_target(object.coordinates, target=coord, visible=lambda: tracker.consistent, tolerance=(0.05, 0.05))
    else:
        await forward_target(object.coordinates, target=(0, 0), visible=lambda: tracker.consistent, tolerance=(0.08, 0.08))
    return True


async def position_harness(object, reference=None):
    return True
