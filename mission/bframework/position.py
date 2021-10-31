import shm
from auv_math.math_utils import rotate
from mission.bframework.task import Task
from mission.bframework.combinators import Concurrent, Sequential
from mission.bframework.movement import RelativeToInitialPositionN, RelativeToInitialPositionE, PositionN, PositionE, Heading, Depth

class WithPositionalControl(Task):
    def run(self, task, enable=True, optimize=False):
        enable_var = shm.navigation_settings.position_controls
        optimize_var = shm.nagivation_settings.optimize
        init_enable, init_optimize = enable_var.get(), optimize_var.get()
        
        enable_var.set(enable)
        optimize_var.set(optimize)

        success = task()
        
        enable_var.set(init_enable)
        optimize_var.set(init_optimize)
        
        return success

class PositionalControl(Task):
    def run(self, enable=True):
        shm.navigation_settings.position_controls.set(enable)
        return True

class MoveXY(Task):
    def run(self, vector, deadband=0.01):
        delta_north, delta_east = rotate(vector, kalman.heading.get())
        n_position = RelativeToInitialPositionN(offset=delta_north, error=deadband)
        e_position = RelativeToInitialPositionE(offset=delta_east, error=deadband)
        success = WithPositionalControl(
                Concurrent(n_position, e_position, finite=False)
        )()
        return success

class MoveAngle(Task):
    def run(self, angle, distance, deadband=0.01):
        return MoveXY(rotate((distance, 0), self.angle), deadband=self.deadband)()

class MoveX(Task):
    def run(self, distance, deadband=0.01):
        return MoveAngle(0, distance, self.deadband)()

class MoveY(Task):
    def run(self, distance, deadband=0.01):
        return MoveAngle(90, distance, self.deadband)()

class GoToPosition(Task):
    def run(self, north, east, heading=None, depth=None, optimize=False, rough=False, deadband=0.05):
        self.north = north
        self.east = east
        
        if heading is None:
            self.heading = shm.navigation_desires.heading.get()
        else:
            self.heading = heading
        
        if depth is None:
            self.depth = shm.navigation_desires.depth.get()
        else:
            self.depth = depth
        
        return WithPositionalControl(
            Concurrent(
                PositionN(self.north, error=deadband),
                PositionE(self.east, error=deadband),
                Heading(self.heading, error=deadband),
                Depth(self.depth, error=deadband)
            ),
            optimize=optimize,
        )()

class CheckDistance(Task):
    def run(self, distance):
        initial_pos = self.pos()
        while self.dist_sq(self.pos(), initial_pos) <= distance ** 2:
            pass
        return True

    def pos(self):
        return [shm.kalman.north.get(), shm.kalman.east.get()]

    def dist_sq(self, p1, p2):
        return (p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2
