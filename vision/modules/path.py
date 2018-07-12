#!/usr/bin/env python3

from collections import namedtuple
from math import radians, atan2, sqrt, sin, cos

import cv2
import numpy as np

import shm
import auvlog.client

import time 

from vision.vision_common import draw_angled_arrow, \
                                 get_angle_from_rotated_rect
from vision.modules.base import ModuleBase
from vision import options as gui_options


log = auvlog.client.log.vision.pipes

vision_options = [ gui_options.IntOption('hsv_s_block_size', 1000, 1, 7500),
                   gui_options.IntOption('hsv_v_block_size', 1000, 1, 7500),
                   gui_options.IntOption('hsv_s_c_thresh', -27, -200, 100),
                   gui_options.IntOption('hsv_v_c_thresh', -27, -200, 100),
                   gui_options.IntOption('lab_a_thresh_min', 0, 0, 255),
                   gui_options.IntOption('lab_a_thresh_max', 143, 0, 255),
                   gui_options.IntOption('erode_size', 4, 0, 50),
                   gui_options.IntOption('dilate_size', 3, 0, 50),
                   gui_options.DoubleOption('min_percent_frame', 0.01, 0, 0.1),
                   gui_options.DoubleOption('max_percent_frame', 0.2, 0, 1),
                   gui_options.IntOption('mask_size', 149, 0, 200),
                   gui_options.IntOption('canny1', 50, 0, 200),
                   gui_options.IntOption('canny2', 150, 0, 200),
                   gui_options.DoubleOption('min_angle_diff', np.pi/8, 0, np.pi*2),
                   gui_options.DoubleOption('min_line_dist', 100, 0, 1000),
                   # A circle with radius 1 inscribed in a square has
                   # 'rectangularity' pi/4 ~ 0.78.
                   gui_options.DoubleOption('aspect_ratio_threshold', 3, 0.5, 5),
                   gui_options.DoubleOption('min_rectangularity', 0.48),
                   gui_options.DoubleOption('heuristic_power', 5),
                   gui_options.BoolOption('debugging', True),
                   gui_options.DoubleOption('min_dist_ratio', 0.4, 0, 2),
                   gui_options.DoubleOption('max_dist_ratio', 2,0, 5),
                   gui_options.DoubleOption('min_line_hough_length',55, 0, 500)
                 ]


segment_info = namedtuple("segment_info", ["x1", "y1", "x2", "y2", "angle", "id", "updated"])
line_info = namedtuple("line_info", ["x1", "y1", "x2", "y2", "angle", "length", "id"])

INVALID_ERROR = 1e99

class Pipes(ModuleBase):
    tracked_lines = []
    

    def angle(self, x1, y1, x2, y2):
        a = atan2(y2-y1, x2-x1)
        a = a - (shm.kalman.heading.get() * np.pi / 180)
        return a

    def abs_angle(self, x1, y1, x2, y2):
        a = atan2(y2-y1, x2-x1)
        return a

    def angle_diff(self, a1, a2):
        # a=min((2*np.pi) - abs(a1-a2), abs(a1-a2))
        a = atan2(sin(a1-a2), cos(a1-a2))
        return abs(a)

    def line_error(self, l, line):
        lx = (l.x1 + l.x2)/2
        ly = (l.y1+l.y2)/2
        linex = (line.x1 + line.x2)/2
        liney = (line.y1 + line.y2)/2
        dist = sqrt((lx-linex)**2 +(ly-liney)**2)
        return dist

    def threshold(self, mat):
        threshes = {}
        hsv = cv2.cvtColor(mat, cv2.COLOR_RGB2HSV)
        hsv_h, hsv_s, hsv_v = cv2.split(hsv)
        s_threshed = cv2.adaptiveThreshold(hsv_s, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 1 + 2 * self.options['hsv_s_block_size'], self.options['hsv_s_c_thresh'])
        v_threshed = cv2.adaptiveThreshold(hsv_v, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 1 + 2 * self.options['hsv_v_block_size'], self.options['hsv_v_c_thresh'])
        
        lab = cv2.cvtColor(mat, cv2.COLOR_RGB2LAB)

        lab_l, lab_a, lab_b = cv2.split(lab)

        lab_a_threshed = cv2.inRange(lab_a, self.options['lab_a_thresh_min'], self.options['lab_a_thresh_max'])

        self.post("lab_a",lab_a_threshed)

        final_threshed = s_threshed & ~lab_a_threshed

        self.post('final_threshed',final_threshed)
        
        threshes["hsv_s"] = s_threshed
        threshes["hsv_v"] = v_threshed
        threshes["final"] = final_threshed
        
        dilate_size = self.options['dilate_size']
        erode_size = self.options['erode_size']
        erode_element = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_size * 2 + 1, erode_size * 2 + 1), (erode_size, erode_size))
        dilate_element = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_size * 2 + 1, dilate_size * 2 + 1), (dilate_size, dilate_size))
        morphed = cv2.erode(final_threshed, erode_element)
        morphed = cv2.dilate(morphed, dilate_element)
        
        threshes["morphed"] = cv2.inRange(final_threshed, 200, 255)
        
        edges = cv2.Canny(morphed,self.options['canny1'],self.options['canny2'],apertureSize = 3)
        threshes["edges"] = edges
        
        if self.options['debugging']:
          for name, image in threshes.items():
            self.post("threshed_{}".format(name), image)

        return threshes

    def find_lines(self, mat, thresh):
        self.post("thres_test",thresh)
        minLineLength = self.options['min_line_hough_length']
        maxLineGap = 100

        lines = cv2.HoughLines(thresh,1,np.pi/180,int(minLineLength))
        #lines = cv2.HoughLines(thresh,10,np.pi/180,100,minLineLength,maxLineGap)

        if lines is None:
          return []

        #print(len(lines))
        if self.options["debugging"]:
          line_image = np.copy(mat)

          for line in lines:
            rho, theta = line[0]
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a * rho
            y0 = b * rho
            x1 = int(x0 + 1000*(-b))
            y1 = int(y0 + 1000*(a))
            x2 = int(x0 - 1000*(-b))
            y2 = int(y0 - 1000*(a))
            cv2.line(line_image,(x1,y1),(x2,y2),(0,255,0),10)


          self.post("all_houghs",line_image)

        #print("initial",len(lines))
        return lines

    #A list of segment_infos sorted in order of best
    def average_lines(self,lines,mat):

      if lines is None:
        return lines

      info = []
      final = []

      for l in lines:

        rho, theta = l[0]
        a = np.cos(theta)
        b = np.sin(theta)
        x0 = a * rho
        y0 = b * rho
        x1 = int(x0 + 1000*(-b))
        y1 = int(y0 + 1000*(a))
        x2 = int(x0 - 1000*(-b))
        y2 = int(y0 - 1000*(a))
        angle = self.angle(x1, y1, x2, y2)
        length = sqrt((y2-y1)**2 + (x2-x1)**2)

        x = line_info(x1,y1,x2,y2, angle, length, 0)
        info.append(x)

      info.sort(key=lambda x: x.length, reverse=True)

      coords = []
        
      num = 0
      angP = None


      for k in info:

        '''
        xac = abs(k.x1 + (k.x1-k.x2) / 2)
        yac = abs(k.y1 + (k.y1-k.y2) / 2)
        '''
        for l in info:
          '''
          xc = abs(l.x1 + (l.x1 - l.x2) / 2)
          yc = abs(l.y1 + (l.y1 - l.y2) / 2)
          '''
        
          if self.angle_diff(l.angle,k.angle) < self.options['min_angle_diff']: # and abs(xc - xac) < self.options['min_line_dist'] and abs(yc - yac) < self.options['min_line_dist']:
            newx1 = k.x1 + (k.x1 - l.x1) / 2
            newx2 = k.x2 + (k.x2 - l.x2) / 2
            newy1 = k.y1 + (k.y1 - l.y1) / 2
            newy2 = k.y2 + (k.y2 - l.y2) / 2

            new_ang = self.angle(newx1, newy1, newx2, newy2)

            k=k._replace(x1=newx1,x2=newx1,y1=newy1,y2=newy2,angle=new_ang)

            
            xac = abs(k.x1 + (k.x1-k.x2) / 2)
            yac = abs(k.y1 + (k.y1-k.y2) / 2)


            info.remove(l)

      if len(info) >= 1:
        final.append(info[0])

        for l in info[1:]:
          if self.angle_diff(info[0].angle, l.angle) > 0.175:
            final.append(l)
            break

      if self.options["debugging"]:
          line_image = np.copy(mat)

          for line in final:
            x1,y1,x2,y2 = line.x1,line.y1,line.x2,line.y2
            cv2.line(line_image,(x1,y1),(x2,y2),(0,255,0),5)


          self.post("final_lines",line_image)

      #print(len(info))
      return final

    def tag(self, mat, text, pos):
        position = (pos[0] - 100, pos[1])
        cv2.putText(mat, text, position, cv2.FONT_HERSHEY_DUPLEX, 1, (0,0,0), thickness=2)

    def seg_to_result(self, l):
        length = sqrt((l.y2-l.y1)**2 + (l.x2-l.x1)**2)
        x = (l.x1 + l.x2)/2
        y = (l.y1 + l.y2)/2
        return result_info(x,y,length,l.angle,l.id)
    '''
    def label_lines(self, lines, lineMat):
        tlines = []
        self.tracked_lines = []

        if lines==None or len(lines) == 0:
          pass

        elif len(self.tracked_lines) == 0 and len(lines) >= 2:
          
          i=1
          lines.sort(key=lambda x:(x.length), reverse=True)
          for l in lines[:2]:
            l2 = segment_info(l.x1, l.y1, l.x2, l.y2, l.angle, i, 0)
            i = i+1
            tlines.append(l2)

          
          lines.sort(key=lambda x:(x.length), reverse=True)
          for index,k in enumerate(lines):
            for l in lines[index+1:]:
              if self.angle_diff(k.angle,l.angle) > 0.4 and self.angle_diff(k.angle, l.angle) < 0.78:
                xck = abs(k.x1 + (k.x2-k.x1) / 2)
                yck = abs(k.y1 + (k.y2-k.y1) / 2)
                xcl = abs(l.x1 + (l.x2-l.x1) / 2)
                ycl = abs(l.y1 + (l.y2-l.y1) / 2)
                line_dist = ((xck-xcl)**2 + (yck-ycl)**2)**0.5

                len_norm = ((k.x1-k.x2)**2 + (k.y1-k.y2)**2)**0.5
                
                if self.options['min_dist_ratio'] < line_dist/len_norm < self.options['max_dist_ratio'] :
                  tlines.append(segment_info(k.x1, k.y1, k.x2, k.y2, k.angle, 1, 0))
                  tlines.append(segment_info(l.x1, l.y1, l.x2, l.y2, l.angle, 2, 0))
                  tlines.sort(key=lambda x:((x.y2 - x.y1)/2 + x.y1), reverse=True)
                  tlines[0] = tlines[0]._replace(id=1)
                  tlines[1] = tlines[1]._replace(id=2)
                  break
            if len(tlines) == 2:
              break
        
        else:
          for line in self.tracked_lines:
            ang = self.options['min_angle_diff'] * (line.updated + 1)
            c=False
            for l in lines:
              if self.line_error(l, line) < 50 * (line.updated + 1):
                l2 = segment_info(l.x1, l.y1, l.x2, l.y2, l.angle, line.id, 0)
                lines.remove(l)
                c=True
            if c:
              tlines.insert(l2.id, l2)
            else:
              l3 = segment_info(line.x1, line.y1, line.x2, line.y2, line.angle, line.id, line.updated + 1)
              tlines.insert(line.id, l3)
        

        self.tracked_lines = tlines
    
    def update_results(self):

        if len(self.tracked_lines) < 2:
          shm.path_results_1.visible.set(0)
          shm.path_results_2.visible.set(0)
          return
        t = self.tracked_lines[0]
        ang = self.abs_angle(t.x1, t.y1, t.x2, t.y2)
        ang = ang / (np.pi) * 180
        self.path_group_1.angle = ang
        x = (t.x1 + t.x2) / 2
        y = (t.y1 + t.y2) / 2
        center = self.normalized((int(x), int(y)))
        self.path_group_1.center_x = center[0]
        self.path_group_1.center_y = center[1]
        # length = sqrt((t.y2-t.y1)**2 + (t.x2-t.x1)**2)
        # self.path_group_1.length = length
        if t.updated == 0:
          self.path_group_1.visible = True
        else:
          self.path_group_1.visible = False
        shm.path_results_1.set(self.path_group_1)

        t = self.tracked_lines[1]
        ang = self.abs_angle(t.x1, t.y1, t.x2, t.y2)
        ang = ang / (np.pi) * 180
        self.path_group_2.angle = ang
        x = (t.x1 + t.x2) / 2
        y = (t.y1 + t.y2) / 2
        center = self.normalized((int(x), int(y)))
        self.path_group_2.center_x = center[0]
        self.path_group_2.center_y = center[1]
        # length = sqrt((t.y2-t.y1)**2 + (t.x2-t.x1)**2)
        # self.path_group_1.length = length
        if t.updated == 0:
          self.path_group_2.visible = True
        else:
          self.path_group_2.visible = False
        shm.path_results_2.set(self.path_group_2)
    '''

    def get_intersection(self, lines):
      x1 = lines[0].x1
      x2 = lines[0].x2
      y1 = lines[0].y1
      y2 = lines[0].y2

      x3 = lines[0].x1
      x4 = lines[0].x2
      y3 = lines[0].y1
      y4 = lines[0].y2

      px= ( (x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4) ) / ( (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4) ) 
      py= ( (x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4) ) / ( (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4) )

      return [px, py]


    def process(self, mat):
      try:
        
        image_size = mat.shape[0]*mat.shape[1]

        self.post('orig', mat)
        threshes = self.threshold(mat)


        lineMat = np.copy(mat)

        lines = self.find_lines(mat, threshes["edges"])
        
        error = namedtuple("error", ["lines", "error"])

        linesI = self.average_lines(lines, mat)

        path_angle = []

        for line in linesI:
          path_angle.append(line.angle)

        if len(linesI) == 2:
          px, py = self.get_intersection(linesI)

        if len(linesI) == 2:
          old_angle_1 = shm.path_results.angle_1.get()
          angle_diff_1 = self.angle_diff(old_angle_1, path_angle[0])
          angle_diff_2 = self.angle_diff(old_angle_1, path_angle[1])
          if angle_diff_1 > angle_diff_2:
            path_angle[0], path_angle[1] = path_angle[1], path_angle[0]

          shm.path_results.angle_1.set(path_angle[0])
          shm.path_results.angle_2.set(path_angle[1])
          shm.path_results.visible_1.set(True)
          shm.path_results.visible_2.set(True)
          shm.path_results.center_x.set(self.normalized(px,1))
          shm.path_results.center_y.set(self.normalized(py,0))
          shm.path_results.num_lines.set(2)

        elif len(linesI) == 1:
          old_angle_1 = shm.path_results.angle_1.get()
          old_angle_2 = shm.path_results.angle_2.get()
          angle_diff_1 = self.angle_diff(old_angle_1, path_angle)
          angle_diff_2 = self.angle_diff(old_angle_2, path_angle)
          if angle_diff_1 < angle_diff_2:
            shm.path_results.angle_1.set(path_angle)
            shm.path_results.visible_1.set(True)
            shm.path_results.visible_2.set(False)
          else:
            shm.path_results.angle_2.set(path_angle)
            shm.path_results.visible_1.set(False)
            shm.path_results.visible_2.set(True)
          shm.path_results.num_lines.set(1)

        else:
          shm.path_results.visible_1.set(False)
          shm.path_results.visible_2.set(False)


        '''
        linesI = self.label_lines(linesI, lineMat)
        
        if self.tracked_lines is not None:
          for l in self.tracked_lines[:2]:
            self.tag(lineMat, str("{}".format(l.id)), (l.x1, l.y1))
            cv2.line(lineMat,(l.x1,l.y1),(l.x2,l.y2),(255,255,255),2)
        '''
        self.post("lines", lineMat)
        

        self.update_results()

      except:
        pass

if __name__ == '__main__':
    Pipes('downward', vision_options)()
