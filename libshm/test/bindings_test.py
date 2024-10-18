#!/usr/bin/env python3
import time
import ctypes
import string
import random
import fnmatch
import threading

from types import ModuleType
from typing import List, Dict, Callable, Any

import shm
import shm.base


def remove_forbidden(lst: List[str]) -> List[str]:
    forbidden_attrs = [
        '__builtins__',
        '__cached__',
        '__doc__',
        '__file__',
        '__loader__',
        '__name__',
        '__package__',
        '__spec__',
        '_fields',
        '_unwatch_*',
        '_watch_*',
        'auv_var_lib',
        'ctypes',
        'shm',
        'watcher',
        'group',
        'add_watcher',
        'remove_watcher',
        'get',
        'set',
    ]

    ret = []
    for item in lst:
        for pattern in forbidden_attrs:
            if fnmatch.fnmatch(item, pattern):
                break
        else:
            ret.append(item)

    return ret


def spoof_group_values(group: shm.base.ShmGrp):
    for field in group._fields_:
        var_name = field[0]
        var_type = field[1]

        if var_type == ctypes.c_int:
            rand_val = random.randint(-2_147_483_648, 2_147_483_647)
            setattr(group, var_name, rand_val)
        elif var_type == ctypes.c_float:
            rand_val = random.random()
            setattr(group, var_name, rand_val)
        elif var_type == ctypes.c_double:
            rand_val = random.random()
            setattr(group, var_name, rand_val)
        else:
            rand_val = ''.join(random.choices(string.ascii_letters, k=8))
            setattr(group, var_name, rand_val.encode())


counter = 0
for shm_module_name in shm.__all__:
    if shm_module_name == 'watchers':
        continue

    counter += 1

    shm_module: ModuleType = getattr(shm, shm_module_name)
    # shm_module: ModuleType = getattr(shm, 'active_mission')
    shm_module_members = dir(shm_module)
    shm_module_members = remove_forbidden(shm_module_members)

    group_get = getattr(shm_module, 'get')
    group_set = getattr(shm_module, 'set')
    group_vars: List[shm.base.ShmVar] = [
        getattr(shm_module, member) for member in shm_module_members]

    # group get and set work
    print(f'{counter}. =========== Testing {shm_module}')

    anonymous_group: shm.base.ShmGrp = group_get()
    spoof_group_values(anonymous_group)
    group_set(anonymous_group)

    anonymous_group_2 = group_get()

    print(f'Part A) {anonymous_group}')
    for field in anonymous_group._fields_:
        var_name = field[0]
        set_value = getattr(anonymous_group, var_name)
        get_value = getattr(anonymous_group_2, var_name)
        print(f'\tmember: {var_name:30} is set to {set_value}')
        assert set_value == get_value

    print(f'Part B) Individual Get/Set')
    for shm_var in group_vars:
        print(f'\t{shm_var}')
        before = shm_var.get()
        shm_var.set(before)
        after = shm_var.get()
        assert before == after

    print(f'Part C) watcher')
    watcher = shm.watchers.watcher()
    watcher.watch(shm_module)
    done = False

    def wait():
        global done
        watcher.wait()
        done = True

    thread_handle = threading.Thread(target=wait)
    thread_handle.start()
    time.sleep(0.005)
    assert done == False, "watcher should stay block"

    # set shm values to what they were supposed to be before
    group_set(anonymous_group)
    thread_handle.join()
    assert done == True, "watcher should release"

    watcher.unwatch(shm_module)
