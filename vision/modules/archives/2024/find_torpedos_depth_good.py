#!/usr/bin/env python3
from vision.modules.base import ModuleBase
from vision import options
from vision.framework.draw import draw_rect, draw_rot_rect
from vision.framework.color import bgr_to_gray
from vision.framework.color import below_threshold
from vision.framework.color import binary_threshold
from vision.framework.color import binary_threshold_inv

from vision.framework.color import range_threshold
from vision.framework.draw import draw_contours
from vision.framework.draw import draw_circle
from vision.framework.feature import outer_contours
from vision.framework.transform import erode
from vision.framework.transform import dilate
from vision.framework.transform import rect_kernel
# from vision.framework.transform import elliptic_kernel
from vision.framework.feature import contour_centroid
from vision.framework.feature import contour_area
from vision.framework.feature import min_enclosing_circle
from vision.framework.feature import min_enclosing_rect
from vision.framework.color import white_balance_bgr, white_balance_bgr_blur
import shm
import math
import numpy as np


module_options = [
  options.IntOption('min_board_thresh', 45, 0, 255),
  options.IntOption('max_board_thresh',200, 0, 255),
  options.IntOption('max_goals_thresh', 45, 0, 255),
]

# assumming no obb in yolo
class DepthTorpedo(ModuleBase):
    def process(self, img):
        #  board
        # gray = bgr_to_gray(img)
        threshed_board = range_threshold(img, self.options['min_board_thresh'],self.options['max_board_thresh'])
        # threshed_board = binary_threshold_inv(img, self.options['min_board_thresh'])
        self.post('orig', img)
        
        eroded = erode(threshed_board,rect_kernel(11))
        dilated = dilate(eroded, rect_kernel(11))
        eroded = erode(dilated, rect_kernel(5))
        dilated = dilate(eroded, rect_kernel(5))

        board_contours = outer_contours(dilated)
        # draw_contours(img,board_contours,thickness = 7)
        self.post('threshed board', threshed_board)
        # self.post('board contours',img)

        board_result = self.find_board(img,board_contours)
        if board_result is not False:
            (board_rect,tr,tl,br,bl) = board_result
            center_x, center_y, width, height, angle = board_rect
            # print('baaa',(tr,tl,br,bl))
            draw_rot_rect(img, center_x, center_y, width, height, angle,color = (255,255,255),thickness=10)
            # draw_contours(img,board_contour,color=(0,0,255),thickness = 7)
            # print(center_x, center_y, width, height, angle)
            self.post('THE board contour', img)

            # goals
            threshed_goals = binary_threshold((img), self.options['max_goals_thresh'])
            eroded = erode(threshed_goals,rect_kernel(7))
            dilated = dilate(eroded, rect_kernel(7))
            eroded = erode(dilated, rect_kernel(5))
            dilated = dilate(eroded, rect_kernel(5))
            goals_contours = outer_contours(dilated)
            # draw_contours(img,goals_contours,thickness = 10)
            # draw_contours(img,goals_contours,color=(255,255,255),thickness = 10)
            # self.post('goals contours', img)
            self.post('threshed goals', threshed_goals)
            goals_circles = self.find_goals(goals_contours,np.array([center_x,center_y]),np.array(tr),np.array(tl),np.array(br),np.array(bl))
            for i in range(len(goals_circles)):
                cent,rad = goals_circles[i]
                print('cent',cent)
                draw_circle(img,cent,int(rad),color = (0,0,0),thickness=10)

            self.post('goals contours', img)


    def find_board(self,img,contours):

        contour_result = self.choose_contour(contours, size_thresh = 100)
        if contour_result is False:
            print('CANNOT FIND DEPTH BOARD')
            return False
        (chosen_contour,chosen_contour_area) = contour_result

        ((center_x, center_y), (width, height), angle) = min_enclosing_rect(chosen_contour)

        center_np = np.array([center_x,center_y])
        diagonal_length = np.sqrt(width**2+height**2)
        diag_ang_rect = np.degrees(np.arctan(height/width))
        tr = (diagonal_length/2) * np.array([np.cos(diag_ang_rect+angle),np.cos(diag_ang_rect+angle)])
        tl = (diagonal_length/2) *np.array([np.cos(diag_ang_rect+angle+90),np.cos(diag_ang_rect+angle+90)])
        br = (diagonal_length/2) *np.array([np.cos(diag_ang_rect+angle+180),np.cos(diag_ang_rect+angle+180)])
        bl = (diagonal_length/2) *np.array([np.cos(diag_ang_rect+angle-90),np.cos(diag_ang_rect+angle-90)])

        area = width*height
        
        norm_x, norm_y = self.normalized((center_x, center_y))

        getattr(shm, f"depth_torpedos_board").angle.set(angle)
        getattr(shm, f"depth_torpedos_board").area.set(area)
        getattr(shm, f"depth_torpedos_board").center_x.set(norm_x)
        getattr(shm, f"depth_torpedos_board").center_y.set(norm_y)
        getattr(shm, f"depth_torpedos_board").visible.set(1)
        getattr(shm, f"depth_torpedos_board").top_right_x.set(tr[0])
        getattr(shm, f"depth_torpedos_board").top_right_y.set(tr[1])

        getattr(shm, f"depth_torpedos_board").top_left_x.set(tl[0])
        getattr(shm, f"depth_torpedos_board").top_left_y.set(tl[1])
        
        getattr(shm, f"depth_torpedos_board").bottom_right_x.set(br[0])
        getattr(shm, f"depth_torpedos_board").bottom_right_y.set(br[1])

        getattr(shm, f"depth_torpedos_board").bottom_left_x.set(bl[0])
        getattr(shm, f"depth_torpedos_board").bottom_left_y.set(bl[1])

        getattr(shm, f"depth_torpedos_board").confidence.set(1)

        # to_print = {
        #     'angle':angle,
        #     'area': area,
        #     'center_x':center_x,
        #     'center_y':center_y,
        #     'visible':1,
        #     'top_right_x':tr[0],
        #     'top_right_y':tl[1],
        #     'top_left_x':tr[0],
        #     'top_left_y':tl[1],
        #     'bottom_right_x':br[0],
        #     'bottom_right_y':br[1],
        #     'bottom_left_x':bl[0],
        #     'bottom_left_y':bl[1]
        # }
        # print('visibility',1)

        # print(to_print)

  
        return ((center_x, center_y, width, height, angle),tr,tl,br,bl)
        # identify the holes within the board
    def choose_contour(self,contours, size_thresh=100):
        if contours == None:
            return False
        if len(contours) == 0:
            return False
        
        max_contour_area = -1
        max_contour = None
        for i in range(len(contours)):
            cont_area = contour_area(contours[i])
            if  (cont_area > max_contour_area) and cont_area >= size_thresh:
                max_contour_area = contour_area(contours[i])
                max_contour = contours[i]
        if max_contour_area < 0:
            return False
        return max_contour,cont_area
    

    def find_goals(self,contours,board_center, tr,tl,br,bl):
        print('finding goals')
    
        max_num = 4
        pos_goals = []
        # corners = [np.array(tr),np.array(tl),np.array(bl),np.array(br)]
        corners = [tr,tl,bl,br]
        for i in range(len(contours)):
            cont = contours[i]
            (center, radius) = min_enclosing_circle(cont)
            center_np = np.array(center)
            if self.in_box(center_np,radius,corners):
                pos_goals.append((cont,center_np,np.pi*radius**2,radius))

        sorted_pos_goals = sorted(pos_goals, key=lambda x: x[2],reverse=True)
        circle_goals = []
        
        visible = 0
        g = 0
        i = 0
        tr_goal = False
        tl_goal = False
        br_goal = False
        bl_goal = False
        all_found = False


        print('num possible goals',len(sorted_pos_goals))
        while i < len(sorted_pos_goals) and all_found is False:

            print('sorting through contours within board',i)

            vert_half_vec = (tr-br)/2
            horiz_half_vec = (br-bl)/2
            tr_quad_corners = [tr,tl+horiz_half_vec,board_center,tr-vert_half_vec]
            tl_quad_corners = [tr-horiz_half_vec,tl,tl-vert_half_vec,board_center]
            bl_quad_corners = [board_center,tl-vert_half_vec,bl,bl+horiz_half_vec]
            br_quad_corners = [br+vert_half_vec,board_center,br-horiz_half_vec,br]
            
            # if its in the top right quadrant
            if tr_goal is False and self.in_box(center_np,radius,tr_quad_corners):
                tr_goal = True
                g = 2
            # if its in the top left quadrant
            elif tl_goal is False and self.in_box(center_np,radius,tl_quad_corners):
                tl_goal = True
                g = 4
            # if its in the bottom left quadrant
            elif bl_goal is False and self.in_box(center_np,radius,bl_quad_corners):
                bl_goal = True
                g = 1
            # if its in the bottom right quadrant
            elif br_goal is False and self.in_box(center_np,radius,br_quad_corners):
                br_goal = True
                g = 3
            else:
                all_found = True
            
            if g == 0:
                return circle_goals

            circle_goals.append(((int(sorted_pos_goals[i][1][0]),int(sorted_pos_goals[i][1][1])),
            sorted_pos_goals[i][3]))
            
            norm_x, norm_y = self.normalized((sorted_pos_goals[i][1][0], sorted_pos_goals[i][1][1]))
            
            getattr(shm, f"depth_goal_{g}").area.set(sorted_pos_goals[i][2])
            getattr(shm, f"depth_goal_{g}").center_x.set(norm_x)
            getattr(shm, f"depth_goal_{g}").center_y.set(norm_y)
            getattr(shm, f"depth_goal_{g}").confidence.set(1)
            getattr(shm, f"depth_goal_{g}").visible.set(visible)
            getattr(shm, f"depth_goal_{g}").radius.set(sorted_pos_goals[i][3])
            getattr(shm, f"depth_goal_{g}").int_num.set(i+1)

        print('num goals visible', len(circle_goals))

        i +=1

        return circle_goals
    
    def in_box(self,center,radius,corners):

        for c in range(4):
            point = corners[c]
            to_goal = center - point

            if c+1 < 4:
                adj_edge = corners[c+1]-point
            else:
                adj_edge = corners[0]-point
# 
            proj_vec = (np.dot(to_goal,adj_edge)/ np.dot(adj_edge,adj_edge)) * adj_edge
            perp_vec = to_goal-proj_vec

            perp_length = np.linalg.norm(perp_vec)

            if (perp_length < radius) or (np.linalg.norm(proj_vec) > np.linalg.norm(adj_edge)):
                return False

        return True
       
if __name__ == '__main__':
  DepthTorpedo("depth", module_options)()
