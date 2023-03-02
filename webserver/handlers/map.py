import json
import tornado.websocket

import shm
from webserver import BaseHandler

class MapSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        """When the socket is opened, send data from the dead_reckoning_virtual
        group to the webgui. Unless all its values are their defaults, in which
        case, send nothing."""
        dead_reckoning = shm.dead_reckoning_virtual.get()
        data = {key: getattr(dead_reckoning, key)
                for key, _ in dead_reckoning._fields_}
        data["pool"] = data["pool"].decode("UTF-8")
        if not all([value == 0 or value == "Teagle" for value in data.values()]):
            self.write_message(json.dumps(data))

    def on_message(self, message):
        """When the socket receives data from the webgui, write it to the
        dead_reckoning_virtual group. Except for the pinger_frequency, which is
        written directly to the hydrophones_pinger_settings group."""
        data = json.loads(message)
        dead_reckoning = shm.dead_reckoning_virtual.get()
        for key, value in data.items():
            if type(value) == str:
                value = value.encode("UTF-8")
            if hasattr(dead_reckoning, key):
                setattr(dead_reckoning, key, value)
        shm.dead_reckoning_virtual.set(dead_reckoning)
        if "pinger_frequency" in data:
            shm.hydrophones_pinger_settings.frequency.set(
                    data["pinger_frequency"])

    def check_origin(self, origin):
        """Allow cross-origin connections. This is necessary for sending data to
        both subs when "Save to SHM" is pressed. It could potentially be changed
        to allow only certain cross-origins in the future, but I'm not terribly
        worried about hacking."""
        return True 

class MapHandler(BaseHandler):
    def get(self):
        self.write(self.render_template("map.html"))
