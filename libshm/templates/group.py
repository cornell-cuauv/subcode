import ctypes

import shm.base
from shm.watchers import watcher

auv_var_lib = shm.base.auv_var_lib

_watch_$!g['groupname']!$ = auv_var_lib.shm_watch_$!g['groupname']!$
_watch_$!g['groupname']!$.argtypes = [ctypes.c_int]
_unwatch_$!g['groupname']!$ = auv_var_lib.shm_unwatch_$!g['groupname']!$
_unwatch_$!g['groupname']!$.argtypes = [ctypes.c_int]

_fields = []
<!--(for k in g['varnames'])-->
    <!--(if g['vars'][k]['type'] == 'string')-->
_fields.append(("$!k!$", ctypes.c_char * ($!g['vars'][k]['length']!$ + 1)))
    <!--(else)-->
_fields.append(("$!k!$", ctypes.$!g['vars'][k]['ptype']!$))
    <!--(end)-->
<!--(end)-->

class group(shm.base.ShmGrp):
    """type representing the $!g['groupname']!$ shared memory group
    """
    _fields_ = _fields

<!--(for k in g['varnames'])-->
    <!--(if g['vars'][k]['type'] == 'string')-->
    $!k!$: bytes
    <!--(else)-->
    $!k!$: ctypes.$!g['vars'][k]['ptype']!$
    <!--(end)-->
<!--(end)-->

    def update(self, **values):
        """unpacked named parameters into the $!g['groupname']!$
        shared memory group
        """
        for key in values.keys():
            self.__setattr__(key, values[key])

def add_watcher(watcher: watcher):
    """register the $!g['groupname']!$ shared memory group to the watcher

    Args:
        watcher (watcher): shared memory group watcher

    Returns:
        Unknown: unknown ctype, pending doc update
    """
    return _watch_$!g['groupname']!$(watcher.watcher_id)

def remove_watcher(watcher: watcher):
    """remove the $!g['groupname']!$ shared memory group from the watcher

    Args:
        watcher (watcher): shared memory group watcher

    Returns:
        Unknown: unknown ctype, pending doc update
    """
    return _unwatch_$!g['groupname']!$(watcher.watcher_id)

def set(g: group):
    """ writes the values in the $!g['groupname']!$ group to shared memory
    """
    auv_var_lib.shm_set_$!g['groupname']!$(g)

auv_var_lib.shm_get_$!g['groupname']!$.restype = group

def get() -> group:
    """reads from shared memory and returns the $!g['groupname']!$ group
    """
    return auv_var_lib.shm_get_$!g['groupname']!$()


<!--(for k in g['varnames'])-->
    <!--(if g['vars'][k]['type'] == 'string')-->
class $!k!$(shm.base.ShmVar):
    _get_$!g['groupname']!$_$!k!$ = auv_var_lib.shm_get_$!g['groupname']!$_$!k!$
    _get_$!g['groupname']!$_$!k!$.argtypes = [ctypes.c_char_p]
    _set_$!g['groupname']!$_$!k!$ = auv_var_lib.shm_set_$!g['groupname']!$_$!k!$
    _set_$!g['groupname']!$_$!k!$.argtypes = [ctypes.c_char_p]

    @classmethod
    def get(cls) -> str:
        """ read shared memory variable

        Returns:
            str: value stored in shm.$!g['groupname']!$.$!k!$
        """
        tmp = ctypes.create_string_buffer($!g['vars'][k]['length']!$ + 1)
        cls._get_$!g['groupname']!$_$!k!$(tmp)
        v=tmp.value
        #decode bytes to str in python3
        return v if type(v)==str else v.decode()

    @classmethod
    def set(cls,value: str):
        """ writes shared memory variable

        Args:
            value (str): value to be stored in shm.$!g['groupname']!$.$!k!$
        """
        cls._set_$!g['groupname']!$_$!k!$(value.encode())

    <!--(else)-->
class $!k!$(shm.base.ShmVar):
    _get = auv_var_lib.shm_get_$!g['groupname']!$_$!k!$
    _get.argtypes = []
    _get.restype = ctypes.$!g['vars'][k]['ptype']!$
    _set = auv_var_lib.shm_set_$!g['groupname']!$_$!k!$
    _set.argtypes = [ctypes.$!g['vars'][k]['ptype']!$]

        <!--(if g['vars'][k]['ptype'] == 'c_int')-->
    @classmethod
    def get(cls) -> int:
        """ read shared memory variable

        Returns:
            int: value stored in shm.$!g['groupname']!$.$!k!$
        """
        return cls._get()

    @classmethod
    def set(cls, value: int):
        """ writes shared memory variable

        Args:
            value (int): value to be stored in shm.$!g['groupname']!$.$!k!$
        """
        cls._set(ctypes.$!g['vars'][k]['ptype']!$(value))
        <!--(end)-->

        <!--(if g['vars'][k]['ptype'] == 'c_float')-->
    @classmethod
    def get(cls) -> float:
        """ read shared memory variable

        Returns:
            float: value stored in shm.$!g['groupname']!$.$!k!$
        """
        return cls._get()

    @classmethod
    def set(cls, value: float):
        """ writes shared memory variable

        Args:
            value (float): value to be stored in shm.$!g['groupname']!$.$!k!$
        """
        cls._set(ctypes.$!g['vars'][k]['ptype']!$(value))
        <!--(end)-->

        <!--(if g['vars'][k]['ptype'] == 'c_double')-->
    @classmethod
    def get(cls) -> float:
        """ read shared memory variable

        Returns:
            double: value stored in shm.$!g['groupname']!$.$!k!$
        """
        return cls._get()

    @classmethod
    def set(cls, value: float):
        """ writes shared memory variable

        Args:
            value (double): value to be stored in shm.$!g['groupname']!$.$!k!$
        """
        cls._set(ctypes.$!g['vars'][k]['ptype']!$(value))
        <!--(end)-->

    <!--(end)-->

<!--(end)-->
