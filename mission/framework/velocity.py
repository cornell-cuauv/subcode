from mission.framework.movement import (_velocity_x, _velocity_x_for_secs,
                                        _velocity_y, _velocity_y_for_secs,
                                        _relative_to_initial_velocity_x, _relative_to_initial_velocity_y,
                                        _relative_to_current_velocity_x, _relative_to_current_velocity_y)
from mission.constants.sub import Tolerance
from typing import Callable

async def velocity_x(target: float, tolerance: float = Tolerance.VELOCITY):
    """
    Set the desired velocity in the forward direction. Velocity should be a value between 
    0 and 1, which corresponds to meters per second (roughly). A velocity_x of 0.3
    should also be the same as pressing [3] in the control helm.

    Args:
        target: The desired forward velocity in meters per second.
        tolerance: The allowable error in the velocity. Defaults to Tolerance.VELOCITY.

    Returns:
        Result of the asynchronous forward velocity setter.
    """
    return await _velocity_x(target, tolerance)

async def velocity_x_for_secs(target: float, duration: float, tolerance: float = Tolerance.VELOCITY):
    """
    Set the desired velocity in the forward direction for a specific duration.

    Args:
        target: The desired forward velocity in meters per second.
        duration: The time in seconds to hold the velocity.
        tolerance: The allowable error in the velocity. Defaults to Tolerance.VELOCITY.

    Returns:
        Result of the asynchronous forward velocity setter for a specific duration.
    """
    return await _velocity_x_for_secs(target, duration, tolerance)

async def relative_to_initial_velocity_x(offset: float, tolerance: float = Tolerance.VELOCITY):
    """
    Set the desired velocity in the forward direction relative to the initial velocity.

    Args:
        offset: The change in velocity relative to the initial value.
        tolerance: The allowable error in the velocity. Defaults to Tolerance.VELOCITY.

    Returns:
        Result of the asynchronous relative-to-initial forward velocity setter.
    """
    return await _relative_to_initial_velocity_x(offset, tolerance)

# def relative_to_current_velocity_x(offset: Callable[[], float], tolerance: float = Tolerance.VELOCITY):
#     """Set the desired velocity in the forward direction relative to the current velocity.

#     Args:
#         offset: A callable that returns the change in velocity.
#         tolerance: The allowable error in the velocity. Defaults to Tolerance.VELOCITY.

#     Returns:
#         Result of the asynchronous relative-to-current forward velocity setter.
#     """
#     return _relative_to_current_velocity_x(offset, tolerance)

async def velocity_y(target: float, tolerance: float = Tolerance.VELOCITY):
    """
    Set the desired velocity in the sideways direction.

    Args:
        target: The desired sideways velocity in meters per second.
        tolerance: The allowable error in the velocity. Defaults to Tolerance.VELOCITY.

    Returns:
        Result of the asynchronous sideways velocity setter.
    """
    return await _velocity_y(target, tolerance)

async def velocity_y_for_secs(target: float, duration: float, tolerance: float = Tolerance.VELOCITY):
    """
    Set the desired velocity in the sideways direction for a specific duration.

    Args:
        target: The desired sideways velocity in meters per second.
        duration: The time in seconds to hold the velocity.
        tolerance: The allowable error in the velocity. Defaults to Tolerance.VELOCITY.

    Returns:
        Result of the asynchronous sideways velocity setter for a specific duration.
    """
    return await _velocity_y_for_secs(target, duration, tolerance)

async def relative_to_initial_velocity_y(offset: float, tolerance: float = Tolerance.VELOCITY):
    """
    Set the desired velocity in the sideways direction relative to the initial velocity.

    Args:
        offset: The change in velocity relative to the initial value.
        tolerance: The allowable error in the velocity. Defaults to Tolerance.VELOCITY.

    Returns:
        Result of the asynchronous relative-to-initial sideways velocity setter.
    """
    return await _relative_to_initial_velocity_y(offset, tolerance)

# def relative_to_current_velocity_y(offset: Callable[[], float], tolerance: float = Tolerance.VELOCITY):
#     """Set the desired velocity in the sideways direction relative to the current velocity.

#     Args:
#         offset: A callable that returns the change in velocity.
#         tolerance: The allowable error in the velocity. Defaults to Tolerance.VELOCITY.

#     Returns:
#         Result of the asynchronous relative-to-current sideways velocity setter.
#     """
#     return _relative_to_current_velocity_y(offset, tolerance)