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
from mission.framework.targeting import ForwardTarget, PIDLoop
from mission.framework.task import Task
from mission.framework.search import SearchFor
from mission.missions.ozer_common import StillHeadingSearch

import shm

CAM_CENTER = (shm.torpedoes_stake.vamp_head_x.get(), shm.torpedoes_stake.vamp_head_y.get())

#At the moment, 90% of the mission is fudged and untested. Proceed with caution.

# @property
# def vamp():
#     return (shm.torpedoes_stake.vamp_head_x.get(), shm.torpedoes_stake.vamp_head_y.get())

def heart():
    return (shm.torpedoes_stake.heart_x.get(), shm.torpedoes_stake.heart_y.get())

def hole():
    return (shm.torpedoes_stake.open_hole_x.get(), shm.torpedoes_stake.open_hole_y.get())

def align_h():
    return shm.torpedoes_stake.align_h.get()

def align_v():
    return shm.torpedoes_stake.align_v.get()

def upper_visible(): 
    return shm.torpedoes_stake.upper_visible.get()

def lower_visible():
    return shm.torpedoes_stake.lower_visible.get()


Search = lambda: Sequential(
        Log('Searching for torpedo board'),
        SearchFor(
            StillHeadingSearch(),
            lambda: upper_visible() or lower_visible(),
            consistent_frames=(1*60, 1.5*60) #TODO: Check consistent frames
            ),
        Zero()
)
# Center = lambda: Sequential(
#         Log('Centering on Vampire Head'),
#         lambda db=0.01875, p=0.0005: ForwardTarget(vamp, target=CAM_CENTER, px=p, py=p, deadband=(db,db)), #TODO: CHECK P VALUES
#         Zero()
# )

class PIDSway(Task):
    def on_first_run(self, *args, **kwargs):
        self.pid_loop = PIDLoop(output_function=VelocityY())

    def on_run(self, error, p=0.0005,  i=0, d=0.0, db=0.01875, negate=False, *args, **kwargs):
        self.pid_loop(input_value=error, p=p, i=i, d=d, target=0, modulo_error=False, deadband = db, negate=negate)

    def stop(self):
        VelocityY(0)()


Point = lambda px=0.3, py=0.0003, p=0.01, d=0.0005, db=0: Concurrent(
            HeadingTarget(point=heart, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            While(lambda: Log("center: %d, %d, target: %d, %d"%(CAM_CENTER[0], CAM_CENTER[1], any_buoy_center()[0], any_buoy_center()[1])), True))


close_to = lambda point1, point2, db=10: abs(point1[0]-point2[0]) < db and abs(point1[1]-point2[1]) < db
aligned = lambda align, db=2: abs(align) < db

def Align(centerf, alignf, visiblef, px=0.15, py=0.0003, p=0.02, d=0.0005, db=0): 
    return MasterConcurrent(
            Consistent(lambda: close_to(centerf(), CAM_CENTER) and aligned(align_any_h()), count=0.3, total=0.5, invert=False, result=True),
            Consistent(visiblef, count=0.2, total=0.3, invert=True, result=False),
            HeadingTarget(point=centerf, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            PIDSway(alignf, p=p, d=d, db=db),
            AlwaysLog(lambda: "align_h: %d"%(alignf(),))) 

CenterBuoy = lambda centerf, visiblef, px=0.004, py=0.0003, d=0.005, db=0: MasterConcurrent(
            Consistent(lambda: close_to(centerf(), CAM_CENTER), count=0.3, total=0.5, invert=False, result=True),
            Consistent(visiblef, count=0.2, total=0.3, invert=True, result=False),
            ForwardTarget(point=centerf, target=CAM_CENTER, px=px, py=py, dx=d, dy=d, deadband=(db,db)), 
            AlwaysLog(lambda: "center: {}, target: {}".format(CAM_CENTER, centerf())))


# AlignNormal = lambda dbt=0.01875, pt=0.0005, pp=0.01875, dbp=0.0005: Sequential(
#         CenterHeart(), #TODO: what to center on?
#         Log('Aligning to normal of torpedo board'),
#         MasterConcurrent(FunctionTask(lambda db=0.05: abs(align_h)<db and abs(align_v)<db), #TODO: make it fail if not visible
#             lambda : HeadingTarget(heart(), target=CAM_CENTER, px=p, py=p, deadband=(db,db)),
#             PIDVelocity(align_h, p=pp, db=dbp)),
#         Zero()
# )

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
CenterHeart= While(lambda db=0, p=0.003, d=0.0005: Sequential(
        Log('Centering on heart'),
        ForwardTarget(heart(), target=CAM_CENTER, px=p, py=p, dx=d, dy=d, deadband=(db,db)), #TODO: CHECK P VALUES
        Zero(),
        Log('Done')
), True)
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
 

Full = \
lambda: Retry(
    lambda: Sequential(
        Log('Starting Stake'),
        Zero(),
        Search(),
        CenterAlign(),
        CenterHeart(),
        TargetTorpedos(),
        BackupRealign(),
        AlignLever(),
        MoveLever(),
        BackupRealign(),
        CenterHole(),
        TargetTorpedos(),
        Log('Stake complete')
    )
, attempts=5) #TODO: What do we do with the retry?
