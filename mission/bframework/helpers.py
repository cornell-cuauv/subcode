from auv_python_helpers.angles import abs_heading_sub_degrees

def call_if_function(value):
    if callable(value):
        return value()
    return value

def within_deadband(a, b, deadband, use_mod_error):
    if use_mod_error:
        return abs_heading_sub_degrees(a, b) < deadband
    return abs(a - b) < deadban
