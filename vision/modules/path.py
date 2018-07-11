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
                   gui_options.IntOption('erode_size', 14, 0, 50),
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
                 ]

def get_zero_path_group():
  path_group = shm.path_results_1.get()
  path_group.angle = 0
  path_group.center_y = 0
  path_group.center_x = 0
  path_group.length = 0
  path_group.visible= False
  return path_group

segment_info = namedtuple("segment_info", ["x1", "y1", "x2", "y2", "angle", "id", "updated"])
line_info = namedtuple("line_info", ["x1", "y1", "x2", "y2", "angle", "length", "id"])

INVALID_ERROR = 1e99

class Pipes(ModuleBase):
    tracked_lines = []
    path_group_1= get_zero_path_group()
    path_group_2= get_zero_path_group()

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
        
        final_threshed = s_threshed - v_threshed
        
        threshes["hsv_s"] = s_threshed
        threshes["hsv_v"] = v_threshed
        threshes["final"] = final_threshed
        '''
        dilate_size = self.options['dilate_size']
        erode_size = self.options['erode_size']
        erode_element = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_size * 2 + 1, erode_size * 2 + 1), (erode_size, erode_size))
        dilate_element = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_size * 2 + 1, dilate_size * 2 + 1), (dilate_size, dilate_size))
        morphed = cv2.erode(final_threshed, erode_element)
        morphed = cv2.dilate(morphed, dilate_element)
        '''
        threshes["morphed"] = cv2.inRange(final_threshed, 200, 255)
        '''
        edges = cv2.Canny(morphed,self.options['canny1'],self.options['canny2'],apertureSize = 3)
        threshes["edges"] = edges
        '''
        if self.options['debugging']:
          for name, image in threshes.items():
            self.post("threshed_{}".format(name), image)

        return threshes

    def find_lines(self, mat, thresh):
        self.post("thres_test",thresh)
        minLineLength = 100
        maxLineGap = 100
        lines = cv2.HoughLinesP(thresh,10,np.pi/180,500,minLineLength,maxLineGap)
        if lines is None:
          return []

        if self.options["debugging"]:
          line_image = np.copy(mat)
          mat_line_image = np.copy(thresh)

          for line in lines:
            x1,y1,x2,y2 = line[0]
            cv2.line(line_image,(x1,y1),(x2,y2),(0,255,0),1)
            cv2.line(mat_line_image,(x1,y1),(x2,y2),(255,0,0),1)


          self.post("all_houghs",line_image)
          self.post("all_houghs_2", mat_line_image)

        return lines

    #A list of segment_infos sorted in order of best
    def average_lines(self,lines,mat):

      if lines is None:
        return lines

      info = []
      final = []

      for l in lines:

        for x1,y1,x2,y2 in l:
          angle = self.angle(x1, y1, x2, y2)
          length = sqrt((y2-y1)**2 + (x2-x1)**2)

        x = line_info(x1,y1,x2,y2, angle, length, 0)
        info.append(x)

      info.sort(key=lambda x: x.length, reverse=True)

      coords = []
        
      num = 0
      angP = None


      for k in info:
        ang = k.angle

        xac = abs(k.x1 + (k.x1-k.x2) / 2)
        yac = abs(k.y1 + (k.y1-k.y2) / 2)

        for l in info:
          xc = abs(l.x1 + (l.x1 - l.x2) / 2)
          yc = abs(l.y1 + (l.y1 - l.y2) / 2)


          if self.angle_diff(l.angle,ang) < self.options['min_angle_diff'] and abs(xc - xac) < self.options['min_line_dist'] and abs(yc - yac) < self.options['min_line_dist']:
            newx1 = k.x1 + (k.x1 - l.x1) / 2
            newx2 = k.x2 + (k.x2 - l.x2) / 2
            newy1 = k.y1 + (k.y1 - l.y1) / 2
            newy2 = k.y2 + (k.y2 - l.y2) / 2

            k=k._replace(x1=newx1,x2=newx1,y1=newy1,y2=newy2)
            
            xac = abs(k.x1 + (k.x1-k.x2) / 2)
            yac = abs(k.y1 + (k.y1-k.y2) / 2)


            info.remove(l)

      for l in info:
        length = sqrt((l.y2-l.y1)**2 + (l.x2-l.x1)**2)
        if length > 100:
          final.append(l)

      if self.options["debugging"]:
          line_image = np.copy(mat)

          for line in final:
            x1,y1,x2,y2 = line.x1,line.y1,line.x2,line.y2
            cv2.line(line_image,(x1,y1),(x2,y2),(0,255,0),1)


          self.post("final_line",line_image)

      return final

    def tag(self, mat, text, pos):
        position = (pos[0] - 100, pos[1])
        cv2.putText(mat, text, position, cv2.FONT_HERSHEY_DUPLEX, 1, (0,0,0), thickness=2)

    def seg_to_result(self, l):
        length = sqrt((l.y2-l.y1)**2 + (l.x2-l.x1)**2)
        x = (l.x1 + l.x2)/2
        y = (l.y1 + l.y2)/2
        return result_info(x,y,length,l.angle,l.id)

    def label_lines(self, lines, lineMat):
        tlines = []
        self.tracked_lines = []

        if lines==None or len(lines) == 0:
          pass

        elif len(self.tracked_lines) == 0 and len(lines) >= 2:
          '''
          i=1
          lines.sort(key=lambda x:(x.length), reverse=True)
          for l in lines[:2]:
            l2 = segment_info(l.x1, l.y1, l.x2, l.y2, l.angle, i, 0)
            i = i+1
            tlines.append(l2)

          '''
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
                
                print(line_dist/len_norm)
                if self.options['min_dist_ratio'] < line_dist/len_norm < self.options['max_dist_ratio'] :
                  tlines.append(segment_info(k.x1, k.y1, k.x2, k.y2, k.angle, 1, 0))
                  tlines.append(segment_info(l.x1, l.y1, l.x2, l.y2, l.angle, 2, 0))
                  tlines.sort(key=lambda x:((x.y2 - x.y1)/2 + x.y1), reverse=True)
                  tlines[0] = tlines[0]._replace(id=1)
                  tlines[1] = tlines[1]._replace(id=2)
                  break
            if len(tlines) == 2:
              break
          
        '''
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
        '''

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


    def process(self, mat):

        time.sleep(0.1)
        image_size = mat.shape[0]*mat.shape[1]

        self.post('orig', mat)
        threshes = self.threshold(mat)


        lineMat = np.copy(mat)

        lines = self.find_lines(mat, threshes["morphed"])
        
        error = namedtuple("error", ["lines", "error"])

        linesI = self.average_lines(lines, mat)
        linesI = self.label_lines(linesI, lineMat)

        if self.tracked_lines is not None:
          for l in self.tracked_lines[:2]:
            self.tag(lineMat, str("{}".format(l.id)), (l.x1, l.y1))
            cv2.line(lineMat,(l.x1,l.y1),(l.x2,l.y2),(255,255,255),2)

        self.post("lines", lineMat)
        

        self.update_results()

if __name__ == '__main__':
    Pipes('downward', vision_options)()
