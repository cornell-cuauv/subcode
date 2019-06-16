from mission.framework.primitive import (
        Zero,
        Log,
        Succeed,
        Fail,
        FunctionTask,
        NoOp
)
from mission.framework.combinators import (
        Sequential,
        Concurrent,
        MasterConcurrent,
        Retry,
        Conditional,
        While
)
from mission.framework.targeting import ForwardTarget, PIDLoop, HeadingTarget
from mission.framework.task import Task
from mission.framework.movement import VelocityY, VelocityX

from mission.missions.will_common import Consistent

import shm

CAM_CENTER = (shm.vamp_buoy_results.camera_x.get, shm.vamp_buoy_results.camera_y.get)

buoys = ("vetalas", "draugr", "aswang", "jiangshi")

b = "draugr"

def buoy_center():
    return (getattr(shm.vamp_buoy_results, "%s_center_x"%b).get, getattr(shm.vamp_buoy_results, "%s_center_y"%b).get)
    # for b in buoys:
    #     if getattr(shm.vamp_buoy_results, "%s_visible"%b).get:
    #         return (getattr(shm.vamp_buoy_results, "%s_center_x"%b).get, getattr(shm.vamp_buoy_results, "%s_center_x"%b).get)

def buoy_size():
    return getattr(shm.vamp_buoy_results, "%s_size"%b).get()

def align_h():
    return getattr(shm.vamp_buoy_results, "%s_align_h"%b).get()    



Search = lambda: Sequential(
        Log('Searching for torpedo board'),
        SearchFor(
            StillHeadingSearch(),
            visible,
            consistent_frames=(1*60, 1.5*60) #TODO: Check consistent frames
            ),
        Zero()
)

class PIDVelocity(Task):
    def on_first_run(self, *args, **kwargs):
        self.pid_loop = PIDLoop(output_function=VelocityY())

    def on_run(self, error, p=0.0005,  i=0, d=0.0, db=0.01875, negate=False, *args, **kwargs):
        self.pid_loop(input_value=error, p=p, i=i, d=d, target=0, modulo_error=False, deadband = db, negate=negate)

    def stop(self):
        RelativeToCurrentVelocityY(0)()
    

Point = lambda px=0.1, py=0.003, p=0.01, d=0.0005, db=0: Concurrent(
            HeadingTarget(buoy_center(), target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            While(lambda: Log("center: %d, %d, target: %d, %d"%(CAM_CENTER[0](), CAM_CENTER[1](), buoy_center()[0](), buoy_center()[1]())), True))

AlignNormal = lambda px=0.1, py=0.003, p=0.03, d=0.0005, db=0: Concurrent(
            HeadingTarget(buoy_center(), target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            PIDVelocity(align_h, p=p, d=d, db=db),
            While(lambda: Log("align_h: %d"%align_h()), True)) #TODO: Make VelY help with centering buoy
# CenterAlign = lambda: Sequential(
#         Center(),
#         AlignNormal()
# )
BackupRealign = lambda:Sequential(
        Log('Backing up to realign with board'),
        MasterConcurrent(Timeout(FunctionTask(lambda: shm.torpedoes_stake.visible), 90), 
            #TODO: Timeout? What's a good time? What happens if it fails?
            RelativeToCurrentVelocityZ(2) #TODO: Is it X or Y or Z? What's a good velocity?
            ),
        Zero(),
        AlignNormal()
)

SIZE_THRESH = 8000
CenterBuoy= lambda px=0.004, py=0.003, d=0.005, db=0: Concurrent(
        ForwardTarget(buoy_center(), target=CAM_CENTER, px=px, py=py, dx=d, dy=d, deadband=(db,db)), #TODO: CHECK P VALUES
        While(lambda: Log("center: %d, %d, target: %d, %d"%(CAM_CENTER[0](), CAM_CENTER[1](), buoy_center()[0](), buoy_center()[1]())), True)
)
Approach = Sequential(
            VelocityX(.2),
            MasterConcurrent(Retry(lambda: Consistent(lambda: buoy_size() > SIZE_THRESH, 0.05, 0.1, False, True), attempts=20), #ADD EITHER LOSE SIGHT OF BUOY
                CenterBuoy(),
                While(lambda: Log("size: %d"%buoy_size()),True)),
            Zero())

TargetTorpedos = lambda: Sequential(
        Log('Aligning shot'),
        Log('Firing')
)
MoveLever = lambda: Sequential( #TODO: DO WE USE MANIPULATORS? CAN WE USE MANIPULATORS?
        Log('Aligning with lever'),
        Log('Moving lever')
)
CenterHole = lambda db=0.01875, p=0.0005: Sequential(
        Log('Centering on Hole'),
        ForwardTarget(board, target=CAM_CENTER, px=p, py=p, deadband=(db,db)) #TODO: CHECK P VALUES
)

OnlyCenter = lambda p = 0.0005, db=10: While(lambda: ForwardTarget(heart(), target=CAM_CENTER, px=p, py=p, deadband=(db,db)), True)
 

