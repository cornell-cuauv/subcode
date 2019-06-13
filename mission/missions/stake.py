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
        Concurrent
        MasterConcurrent,
        Retry,
        Conditional,
        While
)
from mission.framework.targeting import ForwardTarget, ForwardAlign

CAM_CENTER = (0,0)

#At the moment, 90% of the mission is fudged and untested. Proceed with caution.

@property
def vamp():
    return (shm.torpedoes_stake.vamp_head_x.get, shm.torpedoes_stake.vamp_head_y.get)

@property
def heart():
    return (shm.torpedoes_stake.heart_x.get, shm.torpedoes_stake.heart_y.get)

@property
def hole():
    return (shm.torpedoes_stake.open_hole_x.get, shm.torpedoes_stake.open_hole_y.get)

@property
def aligned():
    return shm.torpedoes_stake.aligned.get


Search = lambda: Sequential(
        Log('Searching for torpedo board'),
        SearchFor(
            StillHeadingSearch(),
            shm.torpedoes_stake.vamp_head_visible.get,
            consistent_frames=(1*60, 1.5*60) #TODO: Check consistent frames
            ),
        Zero()
)
Center = lambda: Sequential(
        Log('Centering on Vampire Head'),
        lambda db=0.01875, p=0.0005: ForwardTarget(vamp, target=CAM_CENTER, px=p, py=p, deadband=(db,db)), #TODO: CHECK P VALUES
        Zero()
)
AlignNormal = lambda: Sequential(
        Center(),
        Log('Aligning to normal of torpedo board'),
        MasterConcurrent(FunctionTask(lambda: aligned),
            lambda db=0.01875, p=0.0005: HeadingTarget(vamp, target=CAM_CENTER, px=p, py=p, deadband=(db,db)),
            RelativeToCurrentVelocityY(1)),
        #TODO: Is it X or Y or Z? What's a good velocity? How to determine direction of movement
        Zero()

)
CenterAlign = lambda: Sequential(
        Center(),
        AlignNormal()
)
BackupRealign = lambda:Sequential(
        Log('Backing up to realign with board'),
        MasterConcurrent(Timeout(FunctionTask(lambda: shm.torpedoes_stake.vamp_head_visible), 90), 
            #TODO: Timeout? What's a good time? What happens if it fails?
            RelativeToCurrentVelocityZ(2) #TODO: Is it X or Y or Z? What's a good velocity?
            ),
        Zero(),
        AlignNormal()
)
CenterHeart= lambda: Sequential(
        Log('Centering on heart')
        lambda db=0.01875, p=0.0005: ForwardTarget(heart, target=CAM_CENTER, px=p, py=p, deadband=(db,db)), #TODO: CHECK P VALUES
        Zero()
)
TargetTorpedos = lambda: Sequential(
        Log('Aligning shot'),
        Log('Firing')
)
MoveLever = lambda: Sequential( #TODO: DO WE USE MANIPULATORS? CAN WE USE MANIPULATORS?
        Log('Aligning with lever'),
        Log('Moving lever')
)
CenterHole = lambda: Sequential(
        Log('Centering on Hole'),
        lambda db=0.01875, p=0.005: ForwardTarget(board, target=CAM_CENTER, px=p, py=p, deadband=(db,db)) #TODO: CHECK P VALUES
)

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
        TargetTorpedos()
        Log('Stake complete')
    )
, attempts=5) #TODO: What do we do with the retry?
