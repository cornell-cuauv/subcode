#!/usr/bin/env python3
from mission.framework.base import AsyncBase
# from mission.framework.position import move_x
from mission.framework.movement import *
# from mission.framework.position import *
from mission.framework.targeting import *
from vision.modules.base import ModuleBase
import shm
from mission.framework.consistency import *
import asyncio
from mission.framework.search import *
from mission.framework.actuation import *
import math

class Torpedo(AsyncBase):
    def __init__(self):
        print('init')

        self.goal1Group = shm.depth_goal_1
        self.goal2Group = shm.depth_goal_2
        self.goal3Group = shm.depth_goal_3
        self.goal4Group = shm.depth_goal_4

        self.depthBoardGroup = shm.depth_torpedos_board
        
        depthBoardVisibility = lambda depthBoardGroup: (self.depthBoardGroup.visible.get() == 1)
        goal1Visibility = lambda goal1Group: (self.goal1Group.visible.get() == 1)
        goal2Visibility = lambda goal1Group: (self.goal2Group.visible.get() == 1)
        goal3Visibility = lambda goal1Group: (self.goal3Group.visible.get() == 1)
        goal4Visibility = lambda goal1Group: (self.goal4Group.visible.get() == 1)

        isDepthBoardCentered = lambda depthBoardGroup: (abs(self.depthBoardGroup.center_x.get()) < 0.05 and abs(self.depthBoardGroup.center_y.get()) < 0.05)
        isGoal1Centered = lambda goal1Group: (abs(self.goal1Group.center_x.get()) < 0.05 and abs(self.goal1Group.center_y.get()) < 0.05)
        isGoal2Centered = lambda goal2Group: (abs(self.goal2Group.center_x.get()) < 0.05 and abs(self.goal2Group.center_y.get()) < 0.05)
        isGoal3Centered = lambda goal3Group: (abs(self.goal3Group.center_x.get()) < 0.05 and abs(self.goal3Group.center_y.get()) < 0.05)
        isGoal4Centered = lambda goal4Group: (abs(self.goal4Group.center_x.get()) < 0.05 and abs(self.goal4Group.center_y.get()) < 0.05)

        self.trackerDepthBoardVisibility= SHMConsistencyTracker(self.depthBoardGroup, depthBoardVisibility, (3, 5), (3, 5), False)
        
        self.trackerGoal1Visibility = SHMConsistencyTracker(self.goal1Group, goal1Visibility, (3, 5), (3, 5), False)
        self.trackerGoal1Visibility = SHMConsistencyTracker(self.goal2Group, goal2Visibility, (3, 5), (3, 5), False)
        self.trackerGoal1Visibility = SHMConsistencyTracker(self.goal3Group, goal3Visibility, (3, 5), (3, 5), False)
        self.trackerGoal1Visibility = SHMConsistencyTracker(self.goal4Group, goal4Visibility, (3, 5), (3, 5), False)

        self.trackerGoal1Visibility = SHMConsistencyTracker(self.goal1Group, goal1Visibility, (3, 5), (3, 5), False)

        self.goals_visible_funcs = [self.goal1_visible,self,self.goal2_visible,self.goal3_visible,self.goal4_visible]
        self.goals_point_funcs = [self.goal1_point,self,self.goal2_point,self.goal3_point,self.goal4_point]


        self.first_task = self.main()

    async def main(self):
        for i in range(2):
            target = self.goal_pos(1)
            await forward_target(self.depth_board_visible,target,self.depth_board_point, tolerance=(0.01,0.01))
            await fire_torpedo()
            await fire_torpedo()

    def depth_board_visible(self):
        return self.trackerDepthBoardVisibility.consistent
    
    def depth_board_point(self):
        depth_group = shm.depth_torpedos_board.get()
        return (depth_group.center_x, depth_group.center_y)
    
    def get_orientation(self):
        pass
   
    def goal_pos(goal_num):
        pass

if __name__ == "__main__":
   
   Torpedo().run()