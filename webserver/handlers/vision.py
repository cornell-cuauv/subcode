import json
import traceback
import base64
import cv2
import signal
import tornado.websocket

import numpy as np

from typing import List, Dict, DefaultDict as TDefaultDict, Set, Any
from tornado.web import HTTPError
from tornado.ioloop import PeriodicCallback
from collections import deque, defaultdict

from webserver import BaseHandler

from vision import vision_common
from vision.core.base import ModuleReader
from vision.core.tuners import TunerBase, IntTuner, DoubleTuner, BoolTuner

import shm

websocket_t = tornado.websocket.WebSocketHandler


class GlobalState:
    open_cmfs: Dict[str, ModuleReader] = {}
    websocket_listeners: TDefaultDict[str, Set[websocket_t]] = defaultdict(set)
    message_buffer: TDefaultDict[websocket_t,
                                 List[Dict[str, Any]]] = defaultdict(list)

    def __init__(self):
        pass

    def add_socket_listener(self, module_name: str, listener: websocket_t):
        self.websocket_listeners[module_name].add(listener)
        self.message_buffer[listener] = []

    def remove_socket_listener(self, module_name: str, listener: websocket_t):
        self.websocket_listeners[module_name].remove(listener)
        self.message_buffer[listener] = []

    def refresh_module(self, module_name: str):
        if module_name in self.open_cmfs:
            self.open_cmfs[module_name].unblock()

        mr =  ModuleReader(module_name)
        mr.register_post_udl(self._queue_post_message)
        mr.register_tuner_udl(self._queue_tuner_message)
        mr.run_forever()

        self.open_cmfs[module_name] = mr
        print(f'{module_name} active posts:', mr.active_posts)
        print(f'{module_name} active tuners:', mr.active_tuners)
        
    def refresh_deleted_framework(self):
        active_modules = ModuleReader.get_active_modules() 
        for name, mr in self.open_cmfs.items():
            if mr.framework_deleted and name in active_modules:
                self.refresh_module(name)

    def _queue_post_message(self, module_name: str, name: str, idx: int, data: np.ndarray):
        image = vision_common.resize_keep_ratio(data, 510)
        _, jpeg = cv2.imencode(  # type: ignore
            '.jpg', image, (cv2.IMWRITE_JPEG_QUALITY, 60))  # type: ignore
        jpeg_bytes = base64.encodebytes(jpeg.tobytes()).decode('ascii')

        value_dict = {'image_name': name,
                      'image': jpeg_bytes,
                      'image_index': idx}

        receivers = self.websocket_listeners[module_name]
        for websocket_listener in receivers:
            self.message_buffer[websocket_listener].append(value_dict)

    def _queue_tuner_message(self, module_name: str, name: str, idx: int, tuner: TunerBase):
        if isinstance(tuner, IntTuner):
            msg = {
                'option_name': name,
                'option_index': idx,
                'type': 'int',
                'min_value': tuner._min_value,
                'max_value': tuner._max_value,
                'value': tuner.value
            }

        elif isinstance(tuner, DoubleTuner):
            msg = {
                'option_name': name,
                'option_index': idx,
                'type': 'double',
                'min_value': tuner._min_value,
                'max_value': tuner._max_value,
                'value': tuner.value
            }
        else:
            assert isinstance(tuner, BoolTuner)
            msg = {
                'option_name': name,
                'option_index': idx,
                'type': 'bool',
                'value': tuner.value
            }

        receivers = self.websocket_listeners[module_name]
        for listener in receivers:
            self.message_buffer[listener].append(msg)
        
    def flush_buffer(self):
        for ws, messages in self.message_buffer.items():
            for message in messages:
                ws.write_message(message)
            self.message_buffer[ws].clear()

GLOBAL_STATE = GlobalState()

def sigh(*_):
    for cmf in GLOBAL_STATE.open_cmfs.values():
        cmf.unblock()
    
    raise KeyboardInterrupt

signal.signal(signal.SIGINT, sigh)

class VisionSocketHandler(tornado.websocket.WebSocketHandler):
    periodic_flush = PeriodicCallback(GLOBAL_STATE.flush_buffer, 50)
    periodic_refresh = PeriodicCallback(GLOBAL_STATE.refresh_deleted_framework, 2000)

    def __init__(self, *args, **kwargs):
        super(VisionSocketHandler, self).__init__(*args, **kwargs)
        self.module_name: str = ""

    def open(self, module_name: str, *args, **kwargs):
        print(f"Module '{module_name}' connected to vision gui ")

        # need for auv-webserver.py to have the module name
        # open, so we can register ourselves as a listener
        if module_name not in GLOBAL_STATE.open_cmfs:
            self.close(code=404)

        GLOBAL_STATE.add_socket_listener(module_name, self)
        self.module_name = module_name

        if not self.periodic_flush.is_running():
            print("STARTING PERIODIC FLUSH")
            self.periodic_flush.start()
        
        if not self.periodic_refresh.is_running():
            print("STARTING PERIODIC REFRESH")
            self.periodic_refresh.start()

    
        GLOBAL_STATE.open_cmfs[module_name].allow_resend_tuners_once()


    def on_message(self, message):
        data = json.loads(message)
        name = data['option']
        value = data['value']
        GLOBAL_STATE.open_cmfs[self.module_name].update_tuner_value(name, value)

    def on_close(self):
        print("Connection to vision gui closed")
        if self.module_name != "":
            GLOBAL_STATE.remove_socket_listener(self.module_name, self)
            

# #     def toggle_module(self, module_name):
# #         module = module_name.split("_")[0]
# #         print("Toggling module {}".format(module))
# #         module_var = shm._eval("vision_modules.{}".format(module))
# #         module_var.set(not module_var.get())


class VisionActiveModulesHandler(BaseHandler):
    """ resource with endpoint hosted at /vision/modules/active
    """

    def get(self):
        """ returns user vision modules in JSON list format
        """
        self.write(json.dumps(ModuleReader.get_active_modules()))


class VisionIndexHandler(BaseHandler):
    """ resource with endpoint hosted at /vision
    """

    def get(self):
        """ returns vision template that renders all active modules"""
        self.write(self.render_template("vision_index.html"))


class VisionModuleHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize_module(self, module_name: str):
        GLOBAL_STATE.refresh_module(module_name)
        print("DONE INIT")

    def get(self, module_name: str):
        print(f'Entering {module_name}')

        if module_name not in ModuleReader.get_active_modules():
            raise HTTPError(404)

        if hasattr(shm.vision_modules, module_name):
            module_shm = getattr(shm.vision_modules, module_name)
        else:
            module_shm = None

        if module_shm is not None and not module_shm.get():
            raise HTTPError(412)

        try:
            self.initialize_module(module_name)
        except Exception as e:
            print(e)
            traceback.print_exc()
            raise HTTPError(500)
        return self.write(self.render_template('vision_module.html',
                                               template_values={"title": module_name,
                                                                "module_name": module_name}))

    def write_error(self, status_code, **kwargs):
        if status_code == 404:
            self.finish("Could not find the requested module")
        elif status_code == 412:
            self.finish("That module is not currently running"
                        " i.e. It's controlled by a shm variable and that variable is 0")
        else:
            super(VisionModuleHandler, self).write_error(status_code, **kwargs)
