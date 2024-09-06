"""Helpers are functions that are used in higher level processing.
"""

from vision.framework.feature import contour_centroid, contour_area
import shm
import math

def distance_x(first, second, target, tolerance=0.05):
    """
    Returns: true if contour [first] and [second] are within [target] distance
    with respect to their x-coordinates, plus/minus [tolerance].
    """
    diff = (contour_centroid(first)[0] - contour_centroid(second)[0])
    return target < diff + tolerance and target > diff - tolerance

def distance_y(first, second, target, tolerance=0.05):
    """
    Returns: true if contour [first] and [second] are within [target] distance
    with respect to their y-coordinates, plus/minus [tolerance].
    """
    diff = (contour_centroid(first)[1] - contour_centroid(second)[1])
    return target < diff + tolerance and target > diff - tolerance

def distance_y_percent(first, second, target, percent_tol=0.05):
    """
    Returns: true if contour [first] and [second] are within [target] distance
    with respect to their y-coordinates, plus/minus [tolerance].
    """
    diff = (contour_centroid(first)[1] - contour_centroid(second)[1])
    print("aDFASDF" + str(diff))
    return target < diff * (1 + percent_tol) and target > diff * (1 - percent_tol)


def similar_x(first, second, module, tolerance=0.05):
    """
    Returns: true if contour [first] and [second] have similar x-values, where
    the max allowed distance is [tolerance], which is normalized.
    """
    return distance_x(first, second, module, 0, tolerance)

def similar_y(first, second, module, tolerance=0.05):
    """
    Returns: true if contour [first] and [second] have similar y-values, where
    the max allowed distance is [tolerance], which is normalized.
    """
    return distance_y(first, second, module, 0, tolerance)

def is_reflection(first, second, module, list, tolerance=0.2):
    """
    Determines if contour [first] and [second] are reflections of each other
    by checking similarity of contour x-position similarity of a heuristic function(s),
    which is provided by the client.

    Returns: a tuple (b, c) where [b] is a boolean that indicates a reflection
    has been detected. if [b] is True, then c is the contour that is the
    reflection. if [b] is false, the c is the first value by default.

    first / second: the two contours being compared
    module: reference to the vision module, to access the normalized function
    list: a list of heuristic/characteristic functions to match similarity
    tolerance: tolerance of heuristic comparison
    """
    first_x, first_y = module.normalized(contour_centroid(first))
    second_x, second_y = module.normalized(contour_centroid(second))
    frac = 1 - tolerance
    similar = True
    for heuristic in list:
        if not (frac < heuristic(first) / heuristic(second) and frac < heuristic(second) / heuristic(first)):
            similar = False
            break
    if similar and abs(first_x - second_x) < 0.03:
        if first_y < second_y:
            return (True, 0)
        else:
            return (True, 1)
    return (False, 0)

def distance(c1, c2):
    """
    Determines the distance between coordinates c1 and c2.
    """
    x1, y1 = c1
    x2, y2 = c2
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def in_circle(center, radius, coord):
    """
    Checks if [coord] is within the circle with center [center] and radius [radius].
    """
    xc, yc = center
    x, y = coord
    return radius ** 2 > (xc - x)**2 + (yc - y)**2
    
def name_to_shm(string):
        if string == "earth": 
            return shm.earth_glyph
        elif string == "abydos": 
            return shm.abydos_glyph
        elif string == "dipper": 
            return shm.dipper_glyph
        elif string == "faucet": 
            return shm.faucet_glyph
        elif string == "wishbone": 
            return shm.wishbone_glyph
        elif string == "nozzle": 
            return shm.nozzle_glyph
        elif string == "slingshot": 
            return shm.slingshot_glyph
        elif string == "shovel": 
            return shm.shovel_glyph
        elif string == "curve": 
            return shm.curve_glyph
        elif string == "lightning": 
            return shm.lightning_glyph
        elif string == "dragon": 
            return shm.dragon_glyph
        elif string == "belt": 
            return shm.belt_glyph
        elif string == "claw": 
            return shm.claw_glyph
        else:
            print(string + " is not found!")
            return shm.earth_glyph
