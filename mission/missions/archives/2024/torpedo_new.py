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

        self.yoloBoardGroup = shm.yolo_torpedos_board
        self.depthBoardGroup = shm.depth_torpedos_board
        
        yoloBoardVisibility = lambda yoloBoardGroup: (self.yoloBoardGroup.visible.get() == 1)
        depthBoardVisibility = lambda depthBoardGroup: (self.depthBoardGroup.visible.get() == 1)
        goal1Visibility = lambda goal1Group: (self.goal1Group.visible.get() == 1)
        goal2Visibility = lambda goal1Group: (self.goal2Group.visible.get() == 1)
        goal3Visibility = lambda goal1Group: (self.goal3Group.visible.get() == 1)
        goal4Visibility = lambda goal1Group: (self.goal4Group.visible.get() == 1)

        isYoloBoardCentered = lambda yoloBoardGroup: (abs(self.yoloBoardGroup.center_x.get()) < 0.05 and abs(self.yoloBoardGroup.center_y.get()) < 0.05)
        isDepthBoardCentered = lambda depthBoardGroup: (abs(self.depthBoardGroup.center_x.get()) < 0.05 and abs(self.depthBoardGroup.center_y.get()) < 0.05)
        isGoal1Centered = lambda goal1Group: (abs(self.goal1Group.center_x.get()) < 0.05 and abs(self.goal1Group.center_y.get()) < 0.05)
        isGoal2Centered = lambda goal2Group: (abs(self.goal2Group.center_x.get()) < 0.05 and abs(self.goal2Group.center_y.get()) < 0.05)
        isGoal3Centered = lambda goal3Group: (abs(self.goal3Group.center_x.get()) < 0.05 and abs(self.goal3Group.center_y.get()) < 0.05)
        isGoal4Centered = lambda goal4Group: (abs(self.goal4Group.center_x.get()) < 0.05 and abs(self.goal4Group.center_y.get()) < 0.05)

        self.trackerYoloBoardVisibility = SHMConsistencyTracker(self.yoloBoardGroup, yoloBoardVisibility, (3, 5), (3, 5), False)
        self.trackerDepthBoardVisibility= SHMConsistencyTracker(self.depthBoardGroup, depthBoardVisibility, (3, 5), (3, 5), False)
        
        self.trackerGoal1Visibility = SHMConsistencyTracker(self.goal1Group, goal1Visibility, (3, 5), (3, 5), False)
        self.trackerGoal1Visibility = SHMConsistencyTracker(self.goal2Group, goal2Visibility, (3, 5), (3, 5), False)
        self.trackerGoal1Visibility = SHMConsistencyTracker(self.goal3Group, goal3Visibility, (3, 5), (3, 5), False)
        self.trackerGoal1Visibility = SHMConsistencyTracker(self.goal4Group, goal4Visibility, (3, 5), (3, 5), False)

        self.YoloBoardCentered = SHMConsistencyTracker(self.yoloBoardGroup, isYoloBoardCentered, (3, 5), (3, 5), False)
        self.trackerGoal1Visibility = SHMConsistencyTracker(self.goal1Group, goal1Visibility, (3, 5), (3, 5), False)

        self.goals_visible_funcs = [self.goal1_visible,self,self.goal2_visible,self.goal3_visible,self.goal4_visible]
        self.goals_point_funcs = [self.goal1_point,self,self.goal2_point,self.goal3_point,self.goal4_point]


        self.first_task = self.main()

    async def main(self):
        print('MAIN')
    
        
        # change later
        shm.vision_modules.RedBuoy.set(1)

        if not await self.init_search():
            print('CANNOT FIND BOARD')
            return
        
        while not await self.rough_center_and_approach():
            if not await self.spin(400):
                print("SPIN SEARCH FAILED")

        print("LOW TOLERANCE CENTER")
        await self.center_board_yolo()
        print("align and fire")
        goals_fired = await self.align_and_fire_vision()
        if len(goals_fired) == 2:
            return
        for i in range(1,5):
            if i not in range(goals_fired):
                pass
                
    
        
        # shm.vision_modules.RedBuoy.set(0)

    async def left_and_right_search(self):
        pass
        # currently not doing anything

    async def align_and_fire_vision(self):
        num_fired = 0
        goals_fired = []
        goal_visibility = self.depth_goals_visible()

        for i in range(4):
            result = await forward_target(self.goals_visible_funcs[i], (0,0), self.goals_point_funcs[i], tolerance=(0.01,0.01))
            if result:
                await fire_torpedo()
                goals_fired.append(i+1)  
            if len(goals_fired) >=2:
                return goals_fired
        return goals_fired
    
    async def align_and_fire_no_vision(self,goals):
        for i in range(len(goals)):
            pass

    async def init_search(self):
        
        if  await self.spin(80):
            return True
        if await self.spin(-80):
            return True
        if await self.spin(-80):
            return True
        if await self.spin(80):
            return True
        return False


    async def spin(self, deg):
        while abs(deg) > 5:
            if self.yolo_board_visible():
                print("SPIN SEARCH: board visible, exiting spin search")
                x,y = self.yolo_board_point()
                print(f'spinning {x * 45}')
                await relative_to_initial_heading(x * 45)
                return True
            
            if abs(deg) > 15:
                temp_deg = math.copysign(15, deg)
            else:
                temp_deg = deg
                
            deg = deg-temp_deg
            
            print(f"SPIN SEARCH: Buoy not visible spinning {temp_deg} degrees")
            await relative_to_initial_heading(temp_deg,tolerance=5)

        return False


    async def rough_center_and_approach(self, stop_area = 0.3,max_iterations = 5):
        print('ROUGH CENTER AND APPROACH')
                
        await zero()
        while self.area_filled() < stop_area:
            if not self.yolo_board_visible():
                return False
            elif not self.yolo_board_centered():
                max_iterations -= 1
                
                point = self.yolo_board_point()
                # print(f"Buoy Point: (outbound) {max_iterations} Left")
                # print(f"    x: {point[0]}")
                # print(f"    y: {point[1]}")
                await zero()
                
                if not await self.center_board_yolo(tolerance=(0.2,0.2)):
                    return False
                
                if max_iterations <= 0:
                    return False
            else:
                point = self.yolo_board_point()

                await velocity_x(0.2, tolerance=float('inf'))
                await asyncio.sleep(0.1)

        await zero()        
        return True

    async def center_board_yolo(self,tolerance = (0.07,0.07)):
        print('CENTER BUOY')
        target = (0, 0)
        return await forward_target(self.yolo_board_point, target, self.yolo_board_visible, tolerance=tolerance)
    
    def area_filled(self):
        yolo_group = shm.yolo_torpedos_board.get()
        yolo_area = yolo_group.area

        return yolo_area

    def yolo_board_visible(self):
        # return True
        # print('yolo_board_visible',self.trackerBuoyVisibility.consistent)
        return self.trackerYoloBoardVisibility.consistent

    def yolo_board_point(self):
        yolo_group = shm.yolo_torpedos_board.get()
        return (yolo_group.center_x, yolo_group.center_y)
        # return (0,0)

    def yolo_board_centered(self):
        print('buoy_center',self.trackerBuoyCentered.consistent)
        return self.trackerBuoyCentered.consistent
    
    def depth_board_visible(self):
        return self.trackerDepthBoardVisibility.consistent
    
    def depth_goals_visible(self):

        return (self.trackerGoal1Visibility.consistent,
                self.trackerGoal2Visibility.consistent,
                self.trackerGoal3Visibility.consistent,
                self.trackerGoal4Visibility.consistent)
        
    def goal1_visible(self):
        return self.trackerGoal1Visibility.consistent
    def goal2_visible(self):
        return self.trackerGoal2Visibility.consistent
    def goal3_visible(self):
        return self.trackerGoal3Visibility.consistent
    def goal4_visible(self):
        return self.trackerGoal4Visibility.consistent

    def goal_centered(self,tracker):
        return tracker.consistent
    
    def goal1_point(self):
        goal_group = shm.shm.depth_goal_1
        return (goal_group.center_x, goal_group.center_y)
    def goal2_point(self):
        goal_group = shm.shm.depth_goal_2
        return (goal_group.center_x, goal_group.center_y)
    def goal3_point(self):
        goal_group = shm.shm.depth_goal_3
        return (goal_group.center_x, goal_group.center_y)
    def goal4_point(self):
        goal_group = shm.shm.depth_goal_4
        return (goal_group.center_x, goal_group.center_y)


if __name__ == "__main__":
   Torpedo().run()