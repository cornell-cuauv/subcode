#!/usr/bin/env python3

import curses
import sys
import time
import math
from collections import namedtuple

import shm

# TODO:
#  - efficiency improvements
#  - make code prettier
#  - make a better control helm layout, using the fancy new features?

class StyledString(str):
    """
    Just like a regular string, but with the following style delimiters:
    '*bold text*, @underlined text@, [highlighted text], !blinking text!'.
    They are nestable. Also can do colors: '$<white,red>text$' for white
    text and red background.
    """

    def highlight_if(text, b):
        return StyledString('[{}]'.format(text) if b else text)

# Represents the position of a panel on the screen
Position = namedtuple('Position', ['x', 'y', 'width', 'height'])

def make_position(hv_ind, val_pos, non_val_pos, val_size, non_val_size):
    """
    Handles selecting position of coordinates (horizontal or vertical) based
    on :hv_ind:, i.e. horizontal/vertical indicator. (0 for horizontal, 1 for
    vertical.) I.e. make_position(0, a, b, c, d) = Position(a, b, c, d) and
    make_position(1, a, b, c, d) = Position(b, a, d, c).

    :val_pos:/:non_val_pos: are x/y.
    :val_size:/:non_val_size: are width/height.
    """
    if hv_ind:
        return Position(non_val_pos, val_pos, non_val_size, val_size)
    else:
        return Position(val_pos, non_val_pos, val_size, non_val_size)

class Panel():
    """
    A panel is the basic unit of display on the screen. It is surrounded y a
    box.
    """

    def __init__(self, title=None, width=None, height=None, min_width=0,
                 max_width=math.inf, min_height=0, max_height=math.inf,
                 weight=1, padding=True):

        assert isinstance(weight, int)

        self.title = title
        self.min_width = min_width
        self.min_height = min_height
        self.max_width = width if width is not None else max_width
        self.max_height = height if height is not None else max_height
        self.weight = weight
        self.padding = padding

    def min_dim(self):
        return (self.min_width, self.min_height)

    def max_dim(self):
        return (self.max_width, self.max_height)

    def max_dim_bounded(self):
        return (self.max_width < math.inf, self.max_height < math.inf)

    def get_cols_lines(self, width, height):
        """
        Returns a list of columns, each of which is in turn a list of lines to
        display. :width: and :height: are the maximum size available
        """
        return []

class LineLambdaPanel(Panel):
    """
    A panel that uses a list of content producers to produce each line. If
    :columns:, then the result is pivoted; i.e. a list of rows, each containing
    multiple cells, is converted into a list of columns, each containing
    multiple cells (as required by get_cols_lines() spec).
    """

    def __init__(self, line_lambdas, title=None, columns=False, *args, **kwargs):
        assert isinstance(line_lambdas, list)
        super().__init__(title, *args, **kwargs)
        self.line_lambdas = line_lambdas
        self.columns = columns

    def get_cols_lines(self, width, height):
        out = [f() for f in self.line_lambdas]
        # if self.columns, then pivot output
        # TODO wrap output into multiple columns if it exceeds box height
        return list(map(list, zip(*out))) if self.columns else [out]

def auto_shm_val_fmt(val):
    """
    Returns :val: formatted so that numbers are aligned.
    """
    if isinstance(val, int):
        return '{:3}'.format(val)
    elif isinstance(val, float):
        return '{:7.2f}'.format(val)
    elif isinstance(val, StyledString):
        return val
    else:
        return str(val)

class ShmPanel(LineLambdaPanel):
    """
    A panel that displays a SHM group. Must specify either :group: or
    :variables:, but not both.

    :group: - SHM group to display
    :variables: - list of SHM variables to display
    :select_vars: - optional variable filter (list of variable names),
                    only used when using :group:
    :var_names: - optional variable renaming (list of new names)
    :val_fmt: - function to use for formatting returned values as strings
    """

    def __init__(self, group=None, variables=None, select_vars=None, var_names=None,
                 title='', val_fmt=auto_shm_val_fmt, *args, **kwargs):
        assert (group is not None) ^ (variables is not None)
        if variables is not None:
            assert isinstance(variables, list)
            assert title is not None

        # we can get the title from the group if it is present
        # but let the user disable title by setting to None
        if group is not None and title == '':
            title = group.__name__
        if title == '':
            title = None

        if group is not None:
            if select_vars is None:
                # select all variables
                variables = [getattr(group, field[0]) for field in group._fields]
            else:
                # select only variables specified by select_vars
                variables = [getattr(group, var) for var in select_vars]

        if var_names is not None:
            # apply renamings
            var_name_map = {var: name for var, name in zip(variables, var_names)}
        else:
            var_name_map = {}

        def make_row(v):
            return lambda: ('{}:'.format(var_name_map.get(v, v.__name__)), val_fmt(v.get()))

        line_lambdas = list(map(make_row, variables))

        super().__init__(title=title, line_lambdas=line_lambdas, columns=True, *args, **kwargs)

class Layout(Panel):
    """
    A layout contains panels or other layouts. It defines a list of contents and
    a procedure for determining positions and dimensions for all of its contents
    given a set of dimensions.
    """

    def __init__(self, *contents, **kwargs):
        super().__init__('layout', **kwargs)
        self._contents = contents

    def contents(self):
        """
        Returns the list of contents (layouts or panels).
        """
        return self._contents

    def layout(self, width, height):
        """
        Returns a dict mapping contents to positions.
        """
        return {panel: Position(0, 0, width, height) for panel in self.contents()}

class LinearBox(Layout):
    """
    Lays out contents either horizontally or vertically.
    """

    def __init__(self, vert, *contents, **kwargs):
        super().__init__(*contents, **kwargs)
        # horizontal/vertical indicator (True if vertical)
        self.hv_ind = bool(vert)

        self.cached_dim = None
        self.cached_result = None

        # (width, height), (min, max) - used for calculating appropriate total
        # min/max dimensions
        whmm_funs = ((sum, sum), (lambda x: min(x, default=math.inf),
                                  lambda x: max(x, default=0)))

        self.min_width = max(self.min_width, whmm_funs[not self.hv_ind][0](
            map(lambda p: p.min_width, self.contents())))
        self.max_width = min(self.max_width, whmm_funs[not self.hv_ind][1](
            map(lambda p: p.max_width, self.contents())))
        self.min_height = max(self.min_height, whmm_funs[self.hv_ind][0](
            map(lambda p: p.min_height, self.contents())))
        self.max_height = min(self.max_height, whmm_funs[self.hv_ind][1](
            map(lambda p: p.max_height, self.contents())))

    def layout(self, width, height):
        total_dim = (width, height)

        # don't re-calculate positions if dimensions haven't changed
        if total_dim != self.cached_dim:
            total_bounded_max = 0
            total_bounded_weight = 0
            total_unbounded_weight = 0
            for panel in self.contents():
                if panel.max_dim_bounded()[self.hv_ind]:
                    total_bounded_max += panel.max_dim()[self.hv_ind]
                    total_bounded_weight += panel.weight
                else:
                    total_unbounded_weight += panel.weight
            free_val = total_dim[self.hv_ind] - total_bounded_max

            free_val_per_panel = free_val // total_unbounded_weight \
                if total_unbounded_weight != 0 else 0
            roundoff_leftover = \
                free_val - free_val_per_panel * total_unbounded_weight

            over_full = free_val < 0
            over_full_sub_per_panel = free_val // total_bounded_weight \
                if total_bounded_weight != 0 else 0
            over_full_roundoff_leftover = \
                free_val - over_full_sub_per_panel * total_bounded_weight

            val_counter = 0
            result = {}
            for panel in self.contents():
                if over_full:
                    if panel.max_dim_bounded()[self.hv_ind]:
                        panel_val = int(panel.max_dim()[self.hv_ind]) \
                            + over_full_sub_per_panel * panel.weight
                        if over_full_roundoff_leftover > 0:
                            panel_val += 1
                            over_full_roundoff_leftover -= 1
                    else:
                        panel_val = 0
                else:
                    if panel.max_dim_bounded()[self.hv_ind]:
                        panel_val = int(panel.max_dim()[self.hv_ind])
                    else:
                        panel_val = free_val_per_panel * panel.weight
                        if roundoff_leftover > 0:
                            panel_val += 1
                            roundoff_leftover -= 1
                panel_val = min(max(panel_val, panel.min_dim()[self.hv_ind]),
                                total_dim[self.hv_ind] - val_counter)
                result[panel] = make_position(self.hv_ind, val_counter, 0,
                                              panel_val,
                                              total_dim[not self.hv_ind])
                val_counter += panel_val

            self.cached_result = result

        return self.cached_result

class Hbox(LinearBox):
    """
    Lays out contents horizontally. See LinearBox.
    """
    def __init__(self, *contents, **kwargs):
        super().__init__(False, *contents, **kwargs)

class Vbox(LinearBox):
    """
    Lays out contents vertically. See LinearBox.
    """
    def __init__(self, *contents, **kwargs):
        super().__init__(True, *contents, **kwargs)

# Map of color names to ncurses color constants
color_map = {
    'black': curses.COLOR_BLACK,
    'red': curses.COLOR_RED,
    'green': curses.COLOR_GREEN,
    'yellow': curses.COLOR_YELLOW,
    'blue': curses.COLOR_BLUE,
    'magenta': curses.COLOR_MAGENTA,
    'cyan': curses.COLOR_CYAN,
    'white': curses.COLOR_WHITE,
}

def get_color(c):
    """
    Get an ncurses color constant by name or number.
    """
    if c in color_map:
        return color_map[c]
    else:
        try:
            return int(c)
        except ValueError:
            raise Exception('Invalid color: {}'.format(c))

def text_draw(box, text, max_chars):
    """
    Draw :text: in the ncurses window :box:, up to a maximum of :max_chars:.
    Handles formatting of StyledStrings.
    """

    if isinstance(text, StyledString):
        pos = 0 # pos into string
        pos_disp = 0 # number of chars displayed so far
        attr = 0
        color = 0

        while pos < len(text) and pos_disp < max_chars:
            c = text[pos]
            if c == '*':
                attr ^= curses.A_BOLD
            elif c == '[' and not attr & curses.A_STANDOUT:
                attr ^= curses.A_STANDOUT
            elif c == ']' and attr & curses.A_STANDOUT:
                attr ^= curses.A_STANDOUT
            elif c == '@':
                attr ^= curses.A_UNDERLINE
            elif c == '!':
                attr ^= curses.A_BLINK
            elif c == '$':
                if color:
                    # reset color
                    color = 0
                else:
                    # parse text color format of the form:
                    # '$<fg,bg>text$'
                    pos += 1
                    assert text[pos] == '<'

                    fg_end = text.index(',', pos)
                    fg = get_color(text[pos + 1:fg_end])
                    pos = fg_end

                    bg_end = text.index('>', pos)
                    bg = get_color(text[pos + 1:bg_end])
                    pos = bg_end

                    pair = curses.init_pair(1, fg, bg)
                    color = curses.color_pair(1)
            else:
                box.addstr(c, attr | color)
                pos_disp += 1
            pos += 1
        return pos_disp
    else:
        assert text is not None
        text = text[:max_chars]
        box.addstr(text)
        return len(text)

def panel_draw(screen, panel, pos):
    """
    Draw a panel or layout.
    """

    if isinstance(panel, Layout):
        # this is a layout, so recursively draw children

        layout = panel.layout(pos.width, pos.height)
        for child, child_pos in layout.items():
            panel_draw(screen, child,
                       Position(pos.x + child_pos.x, pos.y + child_pos.y,
                                child_pos.width, child_pos.height))
    elif isinstance(panel, Panel):
        # this is a panel, so draw the panel

        try:
            box = screen.subwin(pos.height, pos.width, pos.y, pos.x)
        except curses.error:
            # it glitches right after resizing
            return

        # draw box around panel
        box.box()

        # one space to either side, one slot taken by box
        text_width = pos.width - 4 if panel.padding else pos.width - 2
        # one slot take by box on top and bottom, one slot take by title
        text_height = pos.height - 2
        text_start_x = 2 if panel.padding else 1
        text_start_y = 1

        if panel.title is not None:
            # display title, centered on first line
            panel_title = panel.title[:text_width]
            panel_title_xpos = \
                2 + math.floor(text_width / 2 - len(panel_title) / 2)
            try:
                box.move(1, panel_title_xpos)
                text_draw(box,
                          StyledString('*{}*'.format(panel_title)), text_width)
            except curses.error:
                pass
            text_height -= 1
            text_start_y += 1

        # this gives us a list of columns, each of which is a list of rows
        # (each containing one cell)
        cols = panel.get_cols_lines(text_width, text_height)
        x_offset = 0
        for col_num, lines in enumerate(cols):
            col_width = 0
            for line_num, line in enumerate(lines[:text_height]):
                try:
                    box.move(line_num + text_start_y, x_offset + text_start_x)
                    line_width = text_draw(box, line,
                                           max(text_width - x_offset, 0))
                    col_width = max(col_width, line_width)
                except curses.error:
                    pass
            # keep one space between columns (if padding enabled)
            x_offset += col_width + (1 if panel.padding else 0)
    else:
        raise Exception('Not a panel or layout!')

def main(screen, panels, callbacks, modal_callbacks, loop_delay):
    """
    Main loop. See start_helm for more information.
    """

    # mode is used for switching between different input modes
    # this is controlled entirely by the provided callbacks
    assert 'default' in modal_callbacks
    mode = 'default'

    curses.curs_set(False)
    screen.nodelay(True)

    while True:
        # detect resizes
        screen_height, screen_width = screen.getmaxyx()

        # process all buffered key presses
        key = screen.getch()
        while key != curses.ERR:
            callback = None

            if key == curses.KEY_RESIZE:
                curses.update_lines_cols()
            elif key in callbacks:
                callback = callbacks[key]
            elif chr(key) in callbacks:
                callback = callbacks[chr(key)]
            elif key in modal_callbacks[mode]:
                callback = modal_callbacks[mode][key]
            elif chr(key) in modal_callbacks[mode]:
                callback = modal_callbacks[mode][chr(key)]

            if callback is not None:
                # invoke callback
                # may optionally return a value to change the mode
                ret = callback()
                if ret is not None:
                    if not ret in modal_callbacks:
                        raise Exception('{} is not a valid mode'.format(ret))
                    mode = ret

            key = screen.getch()

        screen.erase()

        panel_draw(screen, panels, Position(0, 0, screen_width, screen_height))

        screen.refresh()
        time.sleep(loop_delay)

def start_helm(panels, callbacks={}, modal_callbacks={'default': {}},
               loop_delay=0.075):
    """
    Start a helm, as defined by:
    :panels: - the top-level panel or layout
    :callbacks: - a map of characters (or curses key contants) to callback
                  functions; a function may optionally return a value to switch
                  to the mode corresponding to that value
    :modal_callbacks: - a map of modes (e.g. strings) to callback maps for that
                        mode; must contain the 'default' mode, which is loaded
                        at start
    :loop_delay: - time to wait between each display cycle (in seconds)
    """

    try:
        curses.wrapper(main, panels, callbacks, modal_callbacks, loop_delay)
    except KeyboardInterrupt:
        pass

################################################################################
################################################################################

# Below is code for the default control helm, emulating the old control helm.

def build_control_helm(expert=False):
    BATTERY_LOW = 14.2
    BATTERY_EMPTY = 13.0

    assert BATTERY_EMPTY <= BATTERY_LOW

    default_msg = 'EXPERT MODE' if expert else ''

    msg = default_msg
    buf = ''

    def dvl_fmt(val):
        return '{:6.2f}'.format(val)

    def pid_panel(name, rate_name, nav_desire_name):
        desire = getattr(shm.navigation_desires, nav_desire_name)
        value = getattr(shm.kalman, name)
        internal = getattr(shm, 'control_internal_{}'.format(name))
        locked = getattr(shm.control_locked, name)
        rate = getattr(shm.kalman, rate_name)
        settings = getattr(shm, 'settings_{}'.format(name))
        active = getattr(shm.settings_control, '{}_active'.format(name))

        def rd():
            v = auto_shm_val_fmt(settings.rD.get())
            # highlight RD if locked
            return StyledString('[{}]'.format(v)) if locked.get() else v

        return LineLambdaPanel([
            lambda: (' DES:', auto_shm_val_fmt(desire.get()),
                     '   P:', auto_shm_val_fmt(settings.kP.get())),
            lambda: (' VAL:', auto_shm_val_fmt(value.get()),
                     '   I:', auto_shm_val_fmt(settings.kI.get())),
            lambda: (' OUT:', auto_shm_val_fmt(internal.out.get()),
                     '   D:', auto_shm_val_fmt(settings.kD.get())),
            lambda: (' RTE:', auto_shm_val_fmt(rate.get()),
                     '  IG:', auto_shm_val_fmt(internal.integral.get())),
            lambda: (StyledString('   [ON]') if active.get() else '   ON',
                     '  OFF' if active.get() else StyledString('  [OFF]'),
                     '  RD:', rd()),
        ], title=name, width=26, columns=True, padding=False)

    def get_battery_status():
        nonlocal BATTERY_LOW, BATTERY_EMPTY

        status = shm.merge_status.get()
        if status.total_current == 0 and status.total_voltage == 0:
            return ('   Not on vehicle.', ' Monitoring disabled.')
        else:
            voltage_line = '        {:5.2f}V'.format(status.total_voltage)
            if status.total_voltage < BATTERY_EMPTY:
                # manual blinking; we can use ncurses blinking, but it doesn't
                # blink the background
                status_line = \
                    StyledString('$<white,{}>   REPLACE BATTERIES  $'
                                 .format('red' if (time.time() * 10) % 1 < 0.5 \
                                         else 'black'))
            elif status.total_voltage < BATTERY_LOW:
                status_line = \
                        StyledString('$<black,yellow>     Low voltages.    $')
            else:
                status_line = '  Voltages nominal.'
            return (voltage_line, status_line)

    drive_panels = Vbox(
        Hbox(
            LineLambdaPanel([
                lambda: ' PORT: {:4}  '.format(
                    shm.motor_desires.port.get()),
                lambda: ' STAR: {:4}  '.format(
                    shm.motor_desires.starboard.get()),
                lambda: ' FORE:{:3}:{:3} '.format(
                    shm.motor_desires.fore_port.get(),
                    shm.motor_desires.fore_starboard.get()),
                lambda: '  AFT:{:3}:{:3} '.format(
                    shm.motor_desires.aft_port.get(),
                    shm.motor_desires.aft_starboard.get()),
                lambda: ' SFOR: {:4}  '.format(
                    shm.motor_desires.sway_fore.get()),
                lambda: ' SAFT: {:4}  '.format(
                    shm.motor_desires.sway_aft.get()),
            ], width=16, padding=False),

            ShmPanel(shm.navigation_desires, width=20, title=None,
                     padding=False,
                     select_vars=['heading', 'depth', 'pitch',
                                  'roll', 'speed', 'sway_speed'],
                     var_names=[' DES HEAD', ' DES DPTH', ' DES PTCH',
                                ' DES ROLL', ' DES VELX', ' DES VELY']),

            ShmPanel(shm.kalman, width=16, title=None, padding=False,
                     select_vars=['heading', 'depth', 'pitch',
                                  'roll', 'velx', 'vely'],
                     var_names=[' HEAD', ' DPTH', ' PTCH',
                                ' ROLL', ' VELX', ' VELY']),

            LineLambdaPanel([
                lambda: (' DVL ALTD:', dvl_fmt(shm.dvl.savg_altitude.get())),
                lambda: (' DVL TEMP:', dvl_fmt(shm.dvl.temperature.get())),
                lambda: (StyledString.highlight_if(
                    ' DVL BEAM 1', shm.dvl.low_amp_1.get()
                    or shm.dvl.low_correlation_1.get()), '  FWRD:'),
                lambda: (StyledString.highlight_if(
                    ' DVL BEAM 2', shm.dvl.low_amp_2.get()
                    or shm.dvl.low_correlation_2.get()),
                         dvl_fmt(shm.kalman.forward.get())),
                lambda: (StyledString.highlight_if(
                    ' DVL BEAM 3', shm.dvl.low_amp_3.get()
                    or shm.dvl.low_correlation_3.get()), '  SWAY:'),
                lambda: (StyledString.highlight_if(
                    ' DVL BEAM 4', shm.dvl.low_amp_4.get()
                    or shm.dvl.low_correlation_4.get()),
                         dvl_fmt(shm.kalman.sway.get())),
            ], width=20, columns=True, padding=False),

            LineLambdaPanel([
                lambda: StyledString.highlight_if(
                    ' HK ',shm.switches.hard_kill.get()),
                lambda: StyledString.highlight_if(
                    ' SK ', shm.switches.soft_kill.get()),
                lambda: StyledString.highlight_if(
                    ' DV ', shm.dvl.vel_x_invalid.get()
                    or shm.dvl.vel_y_invalid.get()
                    or shm.dvl.vel_z_invalid.get()),
                lambda: StyledString.highlight_if(
                    ' PC ', shm.navigation_settings.position_controls.get()),
                lambda: StyledString.highlight_if(
                    ' OT ', shm.navigation_settings.optimize.get()),
                lambda: StyledString.highlight_if(
                    ' EN ', shm.settings_control.enabled.get()),
            ], width=6, padding=False),
            height=8, min_height=8
        ),

        # PID loop panels
        Hbox(
            pid_panel('heading', 'heading_rate', 'heading'),
            pid_panel('pitch', 'pitch_rate', 'pitch'),
            pid_panel('roll', 'roll_rate', 'roll'),
            height=8,
        ),
        Hbox(
            pid_panel('velx', 'accelx', 'speed'),
            pid_panel('vely', 'accely', 'sway_speed'),
            pid_panel('depth', 'depth_rate', 'depth'),
            height=8,
        ),

        Hbox(
            LineLambdaPanel([
                lambda: get_battery_status()[0],
                lambda: get_battery_status()[1],
            ], width=26),
            LineLambdaPanel([
                lambda: msg,
                lambda: buf,
            ], width=26),
            Panel(width=26),
            height=4,
        ),
    )

    def toggle_shm(var, set_msg=None):
        nonlocal msg
        var.set(not var.get())
        if set_msg is not None:
            msg = set_msg

    def zero(surface):
        nonlocal msg
        desires = shm.navigation_desires.group()
        kalman = shm.kalman.get()
        desires.heading = kalman.heading
        desires.north = kalman.north
        desires.east = kalman.east
        if not surface:
            desires.depth = kalman.depth
        shm.navigation_desires.set(desires)
        msg = 'Surface!' if surface else 'Zero movements'

    def soft_kill(killed):
        nonlocal msg
        shm.switches.soft_kill.set(killed)
        msg = 'KILLED' if killed else 'UNKILLED'

    def toggle_quaternion():
        nonlocal msg
        msg = 'Quaternions broken :('

    drive_callbacks = {
        ' ': (lambda: soft_kill(True)),
        curses.KEY_F5: (lambda: soft_kill(False)),
        '\\': (lambda: soft_kill(False)),
        curses.KEY_F12: (lambda: toggle_shm(shm.settings_control.enabled, 'Toggle Controller')),
        '|': (lambda: toggle_shm(shm.settings_control.enabled, 'Toggle Controller')),
        'n': (lambda: toggle_shm(shm.navigation_settings.position_controls, 'Toggle PosCon')),
        't': (lambda: toggle_shm(shm.navigation_settings.optimize, 'Toggle Trajectories')),
        'z': (lambda: zero(False)),
        'Z': (lambda: zero(True)),
        curses.KEY_LEFT: (lambda: shm.navigation_desires.heading.set(
            (shm.desires.heading.get() - 5) % 360)),
        curses.KEY_RIGHT: (lambda: shm.navigation_desires.heading.set(
            (shm.desires.heading.get() + 5) % 360)),
        curses.KEY_UP: (lambda: shm.navigation_desires.depth.set(
            shm.desires.depth.get() - 0.1)),
        curses.KEY_DOWN: (lambda: shm.navigation_desires.depth.set(
            shm.desires.depth.get() + 0.1)),
        curses.KEY_SLEFT: (lambda: shm.navigation_desires.sway_speed.set(
            shm.desires.sway_speed.get() - 0.1)),
        curses.KEY_SRIGHT: (lambda: shm.navigation_desires.sway_speed.set(
            shm.desires.sway_speed.get() + 0.1)),
        'u': (lambda: shm.navigation_desires.heading.set(
            (shm.desires.heading.get() + 180) % 360)),
        'a': (lambda: 'all'),
        'q': toggle_quaternion,
    }

    default_mode_callbacks = {}

    # for setting speeds
    numbers       = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
    numbers_shift = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')']

    def add_speed_callback(n, ns, speed):
        # speeds go into 'default' mode because we use the same keys for
        # setting values in the PID modes
        default_mode_callbacks[n] = \
            lambda: shm.navigation_desires.speed.set(speed)
        default_mode_callbacks[ns] = \
            lambda: shm.navigation_desires.speed.set(-speed)

    for i, (n, ns) in enumerate(zip(numbers, numbers_shift)):
        add_speed_callback(n, ns, 0.1 * i)

    def toggle_all():
        s = shm.settings_control.get()
        val = not s.heading_active
        s.heading_active = val
        s.pitch_active = val
        s.roll_active = val
        s.velx_active = val
        s.vely_active = val
        s.depth_active = val
        shm.settings_control.set(s)
        return 'default'

    drive_modal_callbacks = {
        'default': default_mode_callbacks,
        'all': {
            'o': toggle_all,
            chr(27): lambda: 'default',
            'c': lambda: 'default',
        },
    }

    def add_buffer_edit_callbacks(callback_dict, commit_callback,
                                  allowed_chars, quit_to_mode='default',
                                  quit_to_msg=default_msg):
        def quit_mode():
            nonlocal msg, buf
            msg = quit_to_msg
            buf = ''
            return quit_to_mode

        def backspace():
            nonlocal buf
            buf = buf[:-1]

        def add_char_callback(char):
            def cb():
                nonlocal buf
                buf += char
            return cb

        def do_commit():
            nonlocal msg, buf
            if commit_callback():
                return quit_mode()
            else:
                buf = ''
                msg = 'Invalid; try again'

        callback_dict.update({
            chr(27): quit_mode,
            'c': quit_mode,
            curses.KEY_BACKSPACE: backspace,
            '\b': backspace,
            '\n': do_commit,
            '\r': do_commit,
        })

        for c in allowed_chars:
            callback_dict[str(c)] = add_char_callback(str(c))

    def add_pid_callbacks(key, name, nav_desire_name, cvt):
        nonlocal msg, buf, expert

        def switch_mode():
            nonlocal msg, buf
            msg = 'Enter {}:'.format(name.title())
            buf = ''
            return name

        def commit():
            val = cvt(buf)
            if val is not None:
                getattr(shm.navigation_desires, nav_desire_name).set(val)
                return True
            return False

        def toggle_pid_loop():
            nonlocal msg, buf
            toggle_shm(getattr(shm.settings_control, '{}_active'.format(name)))
            msg = default_msg
            buf = ''
            return 'default'

        drive_modal_callbacks['default'][key] = switch_mode
        drive_modal_callbacks[name] = {
            'o': toggle_pid_loop
        }
        add_buffer_edit_callbacks(drive_modal_callbacks[name], commit,
                                  list(range(10)) + ['.', '-'])

        if expert:
            def add_expert_control(pid, constant_name):
                nonlocal drive_modal_callbacks

                mode_name = '{}_{}'.format(name, pid)

                def switch_constant_mode():
                    nonlocal msg, buf
                    msg = 'Enter {} {}:'.format(name.title(), constant_name)
                    buf = ''
                    return mode_name

                drive_modal_callbacks[name][pid] = switch_constant_mode

                def commit_const():
                    try:
                        val = float(buf)
                        getattr(getattr(shm, 'settings_{}'.format(name)),
                                constant_name).set(val)
                        return True
                    except ValueError:
                        pass
                    return False

                drive_modal_callbacks[mode_name] = {}
                add_buffer_edit_callbacks(drive_modal_callbacks[mode_name],
                                          commit_const, list(range(10)) + ['.'])

            add_expert_control('p', 'kP')
            add_expert_control('i', 'kI')
            add_expert_control('d', 'kD')

    def converter(min_val, max_val, mult=1):
        def f(val):
            try:
                val_f = float(val)
                if min_val <= val_f <= max_val:
                    return val_f * mult
                else:
                    return None
            except ValueError:
                return None

        return f

    add_pid_callbacks('h', 'heading', 'heading', cvt=converter(0, 360))
    add_pid_callbacks('p', 'pitch', 'pitch', cvt=converter(-90, 90))
    add_pid_callbacks('r', 'roll', 'roll', cvt=converter(-180, 180))
    add_pid_callbacks('x', 'velx', 'speed', cvt=converter(-10, 10, 0.1))
    add_pid_callbacks('y', 'vely', 'sway_speed', cvt=converter(-10, 10, 0.1))
    add_pid_callbacks('d', 'depth', 'depth', cvt=converter(-0.2, 3))

    def add_positional_controls():
        def switch_to_posn():
            nonlocal msg, buf
            msg = 'Enter north position:'
            buf = ''
            return 'posn'

        drive_callbacks['l'] = switch_to_posn

        def commit_pos(name):
            try:
                val = float(buf)
                getattr(shm.navigation_desires, name).set(val)
                return True
            except ValueError:
                pass
            return False

        drive_modal_callbacks['posn'] = {}
        drive_modal_callbacks['pose'] = {}
        allowable_chars = list(range(10)) + ['.', '-']
        add_buffer_edit_callbacks(drive_modal_callbacks['posn'],
                                  lambda: commit_pos('north'), allowable_chars,
                                  quit_to_mode='pose',
                                  quit_to_msg='Enter east position:')
        add_buffer_edit_callbacks(drive_modal_callbacks['pose'],
                                  lambda: commit_pos('north'), allowable_chars)

    add_positional_controls()

    return drive_panels, drive_callbacks, drive_modal_callbacks

if __name__ == '__main__':
    start_helm(*build_control_helm(expert='-e' in sys.argv))
