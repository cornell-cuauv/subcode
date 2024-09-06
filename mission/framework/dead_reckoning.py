import asyncio
import math

import shm
from conf.vehicle import dvl_scaling_factor, dvl_present
from auv_math import math_utils
from mission.framework.movement import heading, velocity_x_for_secs
from mission.framework.position import move_x, go_to_position
from mission.constants.sub import Tolerance

# The list of elements tracked by the dead reckoning system, deduced from the
# variables present in the dead_reckoning_virtual SHM group.
# One of these elements will be 'sub', which refers to the position of the sub
# when transform_coords_to_real_space was called, not its current position.
elements = []
for var in vars(shm.dead_reckoning_virtual).keys():
    if var.endswith('_in_pool'):
        elements.append(var[:-8])

def transform_coords_to_real_space(initial_real_heading : float = None):
    """Transform coordinates from the virtual to the real reference frame.

    The webgui mapper tool uses coordinates in a pool-aligned reference frame,
    wherease the DVL and GX use a far more arbitrary reference frame. This
    function converts the element locations specified in the mapper tool into
    the DVL-GX reference frame so that they can be used by the sub. (The
    former are stored in the dead_reckoning_virtual SHM group and the latter in
    the dead_reckoning_real group.)

    In order for this function to work properly, the sub must be in the position
    in the pool relative to the mission elements which matches the position in
    which the sub appears in the mapper tool. Thus, in a regular autonomous run
    sequence, the sub will first be placed in the water and unkilled, then will
    turn itself in the direction it knows the gate to be, and then finally will
    call this function.

    Only after calling this function should any of the other functions in this
    file be used.

    Note: If initial_real_heading is provided, this function calculates element
    positions and orientations relative to that instead of to the sub's current
    heading. This allows the master mission to save the sub's reference heading
    before the sub is put into the water, but still use the sub's in-water
    position.
    """
    virtual = shm.dead_reckoning_virtual.get()
    real = shm.dead_reckoning_real.get()
    kalman = shm.kalman.get()
    if all([getattr(virtual, key) == 0 or type(getattr(virtual, key)) != int
            for key, _ in virtual._fields_]):
        print("Error: It seems no results from the dead reckoning mapper tool"
                " have been saved to SHM. (Proceeding, but unexpected"
                " behavior will surely ensue.)")
    
    if initial_real_heading is None:
        initial_real_heading = kalman.heading

    for element in elements:
        if not getattr(virtual, element + "_in_pool"):
            setattr(real, element + "_in_pool", 0)
            continue
        setattr(real, element + "_in_pool", 1)

        # The coordinates of the element in virtual space.
        virtual_element_north = getattr(virtual, element + "_north")
        virtual_element_east = getattr(virtual, element + "_east")
        virtual_element_heading = getattr(virtual, element + "_heading", 0)
        depth_at_element = getattr(virtual, "depth_at_" + element)

        # The distances from the sub to the element along the axes of the
        # virtual reference frame.
        virtual_distance_north = virtual_element_north - virtual.sub_north
        virtual_distance_east = virtual_element_east - virtual.sub_east

        # The total distance between the sub and the element, which is the same
        # in virtual as in real space.
        distance = math.sqrt(virtual_distance_north ** 2
                + virtual_distance_east ** 2)

        # The difference between a heading according to the virtual reference
        # frame and the same heading according to the real reference frame.
        # This is where we have to assume that the sub is already facing in the
        # correct direction in the pool.
        virtual_real_heading_offset = initial_real_heading - virtual.sub_heading

        # The heading according to the virtual reference frame at which the sub
        # would have to travel to reach the element.
        virtual_heading_from_sub_to_element = math.atan2(virtual_distance_east,
                virtual_distance_north) * 180 / math.pi

        # The heading according to the real reference frame at which the sub
        # would have to travel to reach the element.
        real_heading_from_sub_to_element = (virtual_heading_from_sub_to_element
                + virtual_real_heading_offset)

        # The distances from the sub to the element along the axes of the real
        # reference frame.
        real_distance_north = (distance
                * math.cos(real_heading_from_sub_to_element * math.pi / 180))
        real_distance_east = (distance
                * math.sin(real_heading_from_sub_to_element * math.pi / 180))

        # The coordinates of the element in real space.
        # This is where we have to assume that the sub is already at the correct
        # location in the pool.
        real_element_north = (kalman.north / dvl_scaling_factor
                + real_distance_north)
        real_element_east = (kalman.east / dvl_scaling_factor
                + real_distance_east)
        
        # The direction according to the real reference frame in which the
        # element is facing.
        real_element_heading = (virtual_element_heading
                + virtual_real_heading_offset)

        setattr(real, element + "_north", real_element_north)
        setattr(real, element + "_east", real_element_east)
        if hasattr(real, element + "_heading"):
            setattr(real, element + "_heading", real_element_heading)
        setattr(real, "depth_at_" + element, depth_at_element)

        # Also set the config if the element is configurable.
        if hasattr(real, element + "_config"):
            config = getattr(virtual, element + "_config")
            setattr(real, element + "_config", config)

    shm.dead_reckoning_real.set(real)

def check_element_validity(element: str):
    """Verify that an element exists and is in the pool.

    Arguments:
    element -- the name of the element
    """
    if element not in elements:
        print("Error: '" + element + "' is not the name of a known element."
                "\n(Known element names: ['" + "', '".join(elements) + "'])")
        return False
    if not getattr(shm.dead_reckoning_real.get(), element + "_in_pool"):
        print("Error: The " + element + " element was marked as not present in"
                " the pool.")
        return False
    return True

def get_element_position(element: str):
    """Return the position (north, east) of an element in the pool."""
    if not check_element_validity(element):
        return None
    dead_reckoning = shm.dead_reckoning_real.get()
    element_north = getattr(dead_reckoning, element + "_north")
    element_east = getattr(dead_reckoning, element + "_east")
    return element_north, element_east

def heading_to_element(target: str):
    """Return the heading from the sub to an element."""
    if not check_element_validity(target):
        return None
    kalman = shm.kalman.get()
    target_north, target_east = get_element_position(target)
    return (math.atan2(target_east - kalman.east / dvl_scaling_factor,
        target_north - kalman.north / dvl_scaling_factor) * 180 / math.pi)

def heading_from_element_to_element(current: str, target: str):
    """Return the heading from one element to another element."""
    if not (check_element_validity(current) and check_element_validity(target)):
        return None
    current_north, current_east = get_element_position(current)
    target_north, target_east = get_element_position(target)
    return (math.atan2(target_east - current_east, target_north - current_north)
            * 180 / math.pi)

def distance_to_element(target: str):
    """Return the distance from the sub to an element."""
    if not check_element_validity(target):
        return None
    kalman = shm.kalman.get()
    target_position = get_element_position(target)
    return math.dist((kalman.north / dvl_scaling_factor,
            kalman.east / dvl_scaling_factor), target_position)

def distance_from_element_to_element(current: str, target: str):
    """Return the distance from one element to another element."""
    if not (check_element_validity(current) and check_element_validity(target)):
        return None
    current_position = get_element_position(current)
    target_position = get_element_position(target)
    return math.dist(current_position, target_position)

async def go_to_element(target: str, stop_dist: float = 0,
        tolerance=Tolerance.POSITION):
    """Send mainsub toward an element.

    Requires the DVL and thus should only be used on mainsub.

    Arguments:
    target    -- the element to which the sub should travel
    stop_dist -- how far from the target element the sub should stop
    tolerance -- how precise the sub needs to be to the stopping point
    """ 
    if not check_element_validity(target):
        return False
    if not dvl_present:
        print("Error: go_to_element requires the DVL.\n(Skipping task. Use"
                " go_from_element_to_element instead.)")
        return False
    north, east = get_element_position(target)
    heading = heading_to_element(target)
    return await go_to_position(north, east, heading)
    # await heading(heading_to_element(target))
    # distance_to_travel = distance_to_element(target) - stop_dist
    # return await move_x(distance_to_travel, tolerance=tolerance)

async def go_from_element_to_element(current: str, target: str,
        speed: float, stop_dist: float = 0):
    """Send the sub from one element to another element.

    Designed for use on minisub. The sub will only end up near the target
    element if it starts near the current element.

    Arguments:
    current   -- the element near which the sub currently is
    target    -- the element to which the sub should travel
    speed     -- how fast the sub should travel
    stop_dist -- how far from the target element the sub should stop
    """
    if not check_element_validity(target):
        return False
    if dvl_present:
        print("Warning: go_to_element is preferable to"
                " go_from_element_to_element when the DVL is available.")
    await heading(heading_from_element_to_element(current, target))
    distance_to_travel = (distance_from_element_to_element(current, target)
            - stop_dist)
    return await velocity_x_for_secs(speed, distance_to_travel / speed * 1.3)

def heading_of_element(element: str):
    """Return the direction in which an element is facing."""
    if not check_element_validity(element):
        return None
    if not hasattr(shm.dead_reckoning_real, element + "_heading"):
        print("Error: No heading is tracked for the " + element + " element.")
        return None
    return getattr(shm.dead_reckoning_real, element + "_heading").get()

def depth_at_element(element: str):
    """Return the depth of the pool at an element's location.

    Careful: This is not the depth of the element itself, but the depth of the
    bottom of the pool below the surface of the pool at the element's
    (north, south) position.
    """
    if not check_element_validity(element):
        return None
    return getattr(shm.dead_reckoning_real, "depth_at_" + element).get()
