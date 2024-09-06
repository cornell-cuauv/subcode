from mission.framework.search import velocity_square_search, velocity_sway_search
from mission.framework.movement import relative_to_initial_heading, velocity_x
import asyncio

# Find Tasks -----------------------

async def foward_search(object):
    """
    foward_search: moves foward until the tracker is consistent.
    """
    tracker = object.consistency_tracker()
    while not tracker.consistent:
        await velocity_x(0.3)
    return True

async def rotate_search(object):
    """
    rotate_search: rotates 360 degrees looking for an object
    nearby. Returns true if found, false if not found.
    """
    for i in range(72):
        if object.is_visible():
            return True
        await relative_to_initial_heading(5)
    return False


async def sway_search(object):
    """
    sway_search: performs a sway search until the tracker
    is consistent.
    """
    tracker = object.consistency_tracker()
    # while True:
    #     await asyncio.sleep(1)
    #     object.is_visible()
    await velocity_sway_search(lambda: tracker.consistent)
    
    return True


async def square_search(object):
    """
    square_search: performs a square search until the tracker
    is consistent.
    """
    tracker = object.consistency_tracker()
    await velocity_square_search(lambda: tracker.consistent)
    return True


async def find_harness(object):
    return True
