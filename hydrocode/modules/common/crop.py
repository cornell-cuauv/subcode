import math

def find_bounds(L_total, L_crop, center):
    """Find the edges of an interval to crop given its size and center.

    The crop size is constrained to the bounds of the full signal.
    E.g. L_total = 10, L_crop = 7, center = 6 => (3, 10)
         L_total = 10, L_crop = 6, center = 6 => (3, 9)
         L_total = 10, L_crop = 6, center = 1 => (0, 6)

    :param L_total: full length of the signal
    :param L_crop: crop length
    :param center: crop center
    :return: crop edges - start included, end not included
    """

    assert L_crop >= 0, 'Crop length must be at least 0'
    assert L_total >= L_crop, (
        'Total length must be at least as large as crop length')

    end = max(min(center + math.ceil(L_crop / 2), L_total), L_crop)
    start = end - L_crop

    return (start, end)