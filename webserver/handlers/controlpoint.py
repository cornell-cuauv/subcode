from webserver import APIHandler
import shm

class ControlpointHandler(APIHandler):
    def get(self, type, var, val):
        try:
            if type == 'absolute':
                getattr(shm.navigation_desires, var).set(float(val))
                self.respond_success(f'navigation_desires.{var} set to {getattr(shm.navigation_desires, var).get()}')
                return
            if type == 'relative':
                init_val = getattr(shm.navigation_desires, var).get()
                getattr(shm.navigation_desires, var).set(init_val + float(val))
                self.respond_success(f'navigation_desires.{var} set to {getattr(shm.navigation_desires, var).get()}')
                return
            self.respond_failure(f'Whoops. Type was {type} but should be either "relative" or "absolute"')
        except:
            self.respond_failure('')