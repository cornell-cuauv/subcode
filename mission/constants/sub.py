from conf.vehicle import is_mainsub

class PidVal:
    """Specifies PID values for each sub's targeting procedures.

    These were last tuned during Summer 2022.
    """
    # Forward / backward targeting.
    PX, IX, DX  = (0.21, 0.02, 0.1) if is_mainsub else (1.4, 0.0, 0.0)
    
    # Leftward / rightward targeting.
    PY, IY, DY  = (0.19156, 0.02, 0.1) if is_mainsub else (1.8, 0.1, 0.64)
    
    # Upward / downward targeting.
    PZ, IZ, DZ  = (1.6, 0.2, 0.02) if is_mainsub else (1.7, 0.0, 0.0)

    # Heading targeting.
    PH, IH, DH  = (40, 0.1, 3) if is_mainsub else (60, 0.15, 20)

    # Downward area targeting.
    PA, IA, DA  = (6, 0.02, 10) if is_mainsub else (4, 0.0, 0.0)

class Tolerance:
    """Specifies tolerances for the movements of each sub.

    Minisub is currently unable to measure its own velocity. Essentially it
    "guesses" thruster speeds based on its desires, and then does not bother
    checking if those guesses are correct; that is, velocity readings remain 0
    in the kalman group. As such we allow an infinite tolerance on minisub so
    that the setters will terminate.

    These were last tuned during Summer 2022.
    """
    VELOCITY    = float('inf') if is_mainsub else float('inf')
    POSITION    = 0.2 if is_mainsub else 0.2
    HEAD        = 2 if is_mainsub else 2
    PITCH       = 10 if is_mainsub else 10
    ROLL        = 10 if is_mainsub else 10
