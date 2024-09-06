#!/usr/bin/env python3

import numpy as np
import sys
import cv2
import math
import pickle
from time import perf_counter

from vision.modules.base import ModuleBase
from vision.modules.ODJ_Vision.base import VisionProcessBase
from vision import options
from vision.framework.color import bgr_to_gray, range_threshold, otsu_threshold
from vision.framework.transform import (elliptic_kernel, morph_close_holes, morph_remove_noise, dilate,
        rotate, translate, resize)
from vision.framework.feature import all_contours, outer_contours, contour_area, min_enclosing_circle, min_enclosing_rect, contour_centroid, simple_canny, canny
from vision.framework.draw import draw_contours, draw_circle, draw_rect, draw_text
from vision.modules.ODJ_Vision.helpers import name_to_shm, distance, in_circle
import shm



filters_list = [
    (lambda x: False if contour_area(x) == 0 else 3.1415926 * min_enclosing_circle(x)[1]**2 / (contour_area(x)) < 8), 
    (lambda x: contour_area(x) >= 1000)
]

glyph_list = ["wishbone", "nozzle", "dipper", "faucet"]

group_a = ["faucet", "dipper"]
group_b = ["wishbone", "nozzle"]

module_options = [
    options.BoolOption('use otsu', False),
    options.BoolOption('use canny', True),
    options.IntOption('close', 7, 0, 21),
    options.IntOption('dilation', 3, 0, 21),
    options.IntOption('max', 65, 0, 255),
    options.IntOption('lower', 200, 0, 255),
    options.IntOption('upper', 255, 0, 255),
    options.IntOption('faucet_error', 150, 0, 500),
    options.IntOption('dipper_error', 3, 0, 500),
    options.IntOption('nozzle_error', 3, 0, 500),
    options.IntOption('wishbone_error', 3, 0, 500),
    options.IntOption('faucet_error_high', 200, 0, 500),
    options.IntOption('dipper_error_high', 50, 0, 500),
    options.IntOption('nozzle_error_high', 50, 0, 500),
    options.IntOption('wishbone_error_high', 50, 0, 500)
]

# for g in glyph_list:
#     module_options.append(options.IntOption(g + "_error", 3, 0, 255))

class Glyph():
    def __init__(self, str):
        with open('vision/modules/ODJ_Vision/objects_2023/pickles/' + str + '.pickle', 'rb') as f:
            self.reference_contour = pickle.load(f)
            self.moments = cv2.moments(self.reference_contour)
            self.reference_hu_moments = cv2.HuMoments(self.moments)
            # boundingRect = cv2.boundingRect(self.reference_contour)
            # self.width_height_ratio = boundingRect[2] / boundingRect[3]
        
        self.visible = False
        """
        Indicates if the Glyph is visible.
        """

        self.contour = None
        """
        The associated contour if the Glyph is visible. If self.visible ==
        False, then the value is meaningless.
        """

        self.corner = ""
        """
        The corner that the Glyph is on. Can be 'TL', 'TR', 'BL', 'BR'. Any
        other values are meaningless, and the associated value is meaningless
        if self.visible == False.
        """

class Region():
    def __init__(self, center, radius, color):
        self.center = center
        self.radius = radius
        self.color = color
        self.contours = []

    def x(self):
        return self.center[0]

    def y(self):
        return self.center[1]
    
    def add_if_contains(self, contour):
        if in_circle(self.center, self.radius, contour_centroid(contour)):
            self.contours.append(contour)
            return True
        return False
    
    def draw(self, img, thickness):
        draw_circle(img, self.center, self.radius, self.color, thickness)

class ContourMoments():
    def __init__(self, contour):
        self.moments = cv2.moments(contour)
        self.hu_moments = cv2.HuMoments(self.moments)



class GlyphVision(VisionProcessBase):
    """
    A structured model for identifying multiple glyphs, specifically for the
    buoy. The motting advantage for detecting multiple glyphs at once is that we
    can remove already detected glyphs as we try find later ones.
    """

    glyph_dict = {}
    """
    glyph_dict : [str : string] : Glyph
    
    Maps each glyph we are trying to identify to a Glyph object,
    which stores information such as visibility on the camera, and its
    associated contour if True.
    
    maps [str] -> Glyph([str])
    """

    glyph_moments = {}
    """
    glyph_moments : [contour : contour] : (moment * hu_moment)

    Maps each contour on the image to its moment and hu_moment.
    """
    
    def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      for g in glyph_list:
        self.glyph_dict[g] = Glyph(g)
    
    def color_filter(self, img):
        self.post('original', img)
        gray, _ = bgr_to_gray(img)
        if self.options['use otsu']:
            _, threshed = otsu_threshold(gray)
            threshed = ~threshed
        elif self.options['use canny']:
            threshed = canny(gray, self.options['lower'], self.options['upper'])
        else:
            threshed = range_threshold(gray, 0, self.options['max'])
        threshed = morph_close_holes(threshed, elliptic_kernel(self.options['close']))
        threshed = dilate(threshed, elliptic_kernel(self.options['dilation']))
        self.post('threshed', threshed)
        self.clist = outer_contours(threshed)
    
    def higher_process(self, img):        
        for g in self.glyph_dict:
            self.glyph_dict[g].visible= False
        # store contours and their moments for rapid lookup
        self.glyph_moments = {}
        for c in self.clist:
            self.glyph_moments[contour_centroid(c)] = ContourMoments(c)
        
        def error(contour, target):
            """
            Calculates error of hu moment of [contour] with respect to [target].
            contour : the contour being """
            result = 0
            # boundingRect = cv2.boundingRect(contour)
            # width_scale_factor = self.glyph_dict[target].width_height_ratio * boundingRect[3] / boundingRect[2]
            # print(width_scale_factor)
            # contour_scaled = np.array(list(map(lambda p: [[int(p[0][0] * width_scale_factor), int(p[0][1])]], contour.tolist())))
            # print(contour_scaled)
            cm = self.glyph_moments[contour_centroid(contour)]
            moments = cm.moments
            hu_moments = cm.hu_moments
            for ref_moment, moment in zip(self.glyph_dict[target].reference_hu_moments, hu_moments):
                result += (-1 * (moment / abs(moment)) * math.log10(abs(moment)) + 1 * (ref_moment / abs(ref_moment)) * math.log10(abs(ref_moment))) ** 2
            return result[0]

        # independent, identical search for each buoy
        def shotgun():
          if len(self.clist) > 0:
              for g in glyph_list:
                  if len(self.clist) > 0:
                      self.clist = list(sorted(self.clist, key=lambda x : error(x, g)))
                      # print(list(map(lambda x : error(x, g), self.clist)))
                      best_contour = self.clist[0]
                      if error(best_contour, g) < self.options[g + '_error']:
                          self.glyph_dict[g].visible = True
                          self.glyph_dict[g].contour = best_contour
                          #self.clist.remove(best_contour)
                          self.clist_final.append(best_contour)
                          self.clist_draw[g] = contour_centroid(best_contour)
                      else:
                          self.glyph_dict[g].visible = False
                          
        # generation of glyphs one at a time
        def generate():
            if len(self.clist) > 0:
                glyphs = glyph_list.copy()

                # initial scan for the first contour
                err, best, con = float("inf"), None, None
                radius = 0
                for g in glyphs:
                    self.clist = list(sorted(self.clist, key=lambda x : error(x, g)))
                    best_contour = self.clist[0]
                    e = error(best_contour, g)
                    # if e < self.options[g + '_error'] and e < err:
                    if g == 'wishbone':
                        err = e
                        best = g
                        con = best_contour
                # self.clist.pop(0) # remove selected glyph from remaining list
                glyphs.remove(g)
                self.clist_draw[best] = contour_centroid(con)
                for c in self.clist:
                    x, y = contour_centroid(c)
                    x = int(x); y = int(y)
                    draw_circle(img, (x, y), 2, (255, 255, 0), 5)

                # next, create areas where contours could be spotted
                if con is not None:
                    (x, y), r = min_enclosing_circle(con)
                    x, y, r = int(x), int(y), int(r)
                    draw_circle(img, (x, y), r, (255, 255, 255), 3)
                    self.clist_final.append(con)
                    self.clist_draw[best] = x, y
                    side_dist = 2*r
                    diag_dist = int(2*r)
                    list_sides = ((x + side_dist, y), (x - side_dist, y), (x, y + side_dist), (x, y - side_dist))
                    list_diag = ((x + diag_dist, y + diag_dist), (x - diag_dist, y + diag_dist), (x + diag_dist, y - diag_dist), (x - diag_dist, y - diag_dist))
                    r_new = int(10/8 * r)
                    radius = r_new
                    for coord in list_sides:
                        draw_circle(img, coord, r_new, (255, 0, 0), 3)
                    for coord in list_diag:
                        draw_circle(img, coord, r_new, (0, 0, 255), 3)

                    # for the remaining glyphs, match based on proximity of the 8 bounding circles

                    a, b = group_a.copy(), group_b.copy()
                    diag, side = None, None
                    if best in group_a: # group_a = diagonal, group_b = sides
                        print("A")
                        a.remove(best)
                        diag, side = a, b
                    else: # group_a = sides, group_b = diagonal
                        print("B")
                        b.remove(best)
                        diag, side = b, a
                        pass

                    diag_group = []
                    best, con = None, None
                    for center in list_diag:
                        for con in self.clist:
                            if in_circle(center, radius, contour_centroid(con)):
                                diag_group.append((center, con))
                    if len(diag_group) > 0:
                        _, con_best = min(diag_group, key = lambda x: error(x[1], diag[0]) * distance(x[0], contour_centroid(con)))
                        self.clist_draw[diag[0]] = contour_centroid(con_best)
                        self.clist_final.append(con_best)
                    
                    side_group = []
                    for center in list_sides:
                            for con in self.clist:
                                if in_circle(center, radius, contour_centroid(con)):
                                    side_group.append((center, con))
                    for s in side:
                        if len(side_group) > 0:
                            a, con_best = min(side_group, key = lambda x: error(x[1], s) * distance(x[0], contour_centroid(con)))
                            self.clist_draw[s] = contour_centroid(con_best)
                            self.clist_final.append(con_best)
                            side_group.remove((a, con_best))
                    # side
        
        # generation of glyphs one at a time, with better tracking / memoization
        def generate2():
            processed_glyphs = []

            # generation begins here
            if len(self.clist) > 0:
                glyphs = glyph_list.copy()

                # initial scan for the first contour
                err, best, con = float("inf"), None, None
                for g in glyphs:
                    self.clist = list(sorted(self.clist, key=lambda x: error(x, g)))
                    best_contour = self.clist[0]
                    e = error(best_contour, g)
                    # if e < self.options[g + '_error'] and e < err:
                    if e < self.options[g + '_error'] and e < err:
                        err = e
                        best = g
                        con = best_contour
                        
                # next, create areas where contours could be spotted
                # store each contour in respective circle
                if con is not None:
                    glyphs.remove(best)
                    processed_glyphs.append(best)
                    self.clist_draw[best] = contour_centroid(con)
                    
                    for c in self.clist:
                        x, y = contour_centroid(c)
                        x = int(x); y = int(y)
                        draw_circle(img, (x, y), 2, (255, 255, 0), 5)

                    self.glyph_dict[best].contour = con
                    self.glyph_dict[best].visible = True # shm
                    (x, y), r = min_enclosing_circle(con)
                    x, y, r = int(x), int(y), int(r)
                    draw_circle(img, (x, y), r, (255, 255, 255), 3)
                    self.clist_final.append(con)
                    self.clist_draw[best] = x, y
                    side_dist = int(2*r); diag_dist = int(2.4*r)
                    side_r = int(r); diag_r = int(10/6 * r)

                    # produce the four local regions
                    side_regions = {
                        "top"           : Region((x, y - side_dist), side_r, (255, 0, 0)),
                        "bottom"        : Region((x, y + side_dist), side_r, (255, 0, 0)),
                        "left"          : Region((x - side_dist, y), side_r, (255, 0, 0)),
                        "right"         : Region((x + side_dist, y), side_r, (255, 0, 0))
                    }

                    for c in side_regions:
                        side_regions[c].draw(img, 3)
                        for contour in self.clist:
                            side_regions[c].add_if_contains(contour)
                        draw_text(img, str(len(side_regions[c].contours)), side_regions[c].center, 2, (255, 0, 0), 3)
                        
                    diag_regions = {
                        "top_left"      : Region((x - diag_dist, y - diag_dist), diag_r, (0, 0, 255)),
                        "top_right"     : Region((x + diag_dist, y - diag_dist), diag_r, (0, 0, 255)),
                        "bottom_left"   : Region((x - diag_dist, y + diag_dist), diag_r, (0, 0, 255)),
                        "bottom_right"  : Region((x + diag_dist, y + diag_dist), diag_r, (0, 0, 255))
                    }

                    for c in diag_regions:
                        diag_regions[c].draw(img, 3)
                        for contour in self.clist:
                            diag_regions[c].add_if_contains(contour)
                        draw_text(img, str(len(diag_regions[c].contours)), diag_regions[c].center, 2, (0, 0, 255), 3)

                    # find the complementary glyph to the first one
                    (diag, side) = (group_a.copy(), group_b.copy()) if best in group_a else (group_b.copy(), group_a.copy())
                    diag.remove(best)
                    err, contour, reg = float("inf"), None, None
                    for r in diag_regions:
                        for c in diag_regions[r].contours:
                            e = error(c, diag[0]) # * * distance(diag_regions[r].center, contour_centroid(con))
                            # print("IUDASFADSKF" + str(e))
                            if e < self.options[diag[0] + "_error_high"] and e < err:
                                err, contour, reg = e, c, r
                    
                    # complementary glyph found, now find the other two in the two remaining regions
                    if contour is not None:
                        self.clist_final.append(contour)
                        draw_text(img, diag[0], contour_centroid(contour), 1.5, (0, 0, 0), 3)
                        self.glyph_dict[diag[0]].contour = contour
                        self.glyph_dict[diag[0]].visible = True
                        selected_sides = reg.split("_") # irst one is top/bottom, second is left/right. guaranteed
                        diag_regions[reg].draw(img, 15)

                        processed_glyphs.append(diag[0])
                        pos_assignments = None
                        if reg == "top_left":
                            pos_assignments = ("BR", "TL")
                        elif reg == "top_right":
                            pos_assignments = ("BL", "TR")
                        elif reg == "bottom_left":
                            pos_assignments = ("TR", "BL")
                        elif reg == "bottom_right":
                            pos_assignments = ("TL", "BR")
                        else:
                            print("wtf")
                        for i in range(2):
                            self.glyph_dict[processed_glyphs[i]].corner = pos_assignments[i]
                        
                        for g in self.glyph_dict:
                            if self.glyph_dict[g].visible:
                                x, y = contour_centroid(self.glyph_dict[g].contour)
                                draw_text(img, self.glyph_dict[g].corner, (x + 50, y + 50), 2, (0, 0, 0), 9)
                                                
                        for region in selected_sides: # "top", "left"
                            side_regions[region].draw(img, 15)
                        err, contour_map = float("inf"), {}
                        for possible_maps in [{selected_sides[0]:side[0], selected_sides[1]:side[1]}, {selected_sides[0]:side[1], selected_sides[1]:side[0]}]: # "e.g. top" -> "faucet", or "top" -> "dipper"
                            map_error, current_cmap = 1, {}
                            for m in possible_maps:
                                glyph = possible_maps[m]
                                contour_error = float("inf")
                                for c in side_regions[m].contours:
                                    e = error(c, glyph)
                                    if e < contour_error:
                                        contour_error = e
                                        current_cmap[possible_maps[m]] = (c, m)
                                        print(m)
                                map_error *= contour_error
                            if map_error < err:
                                err = map_error
                                contour_map = current_cmap
                        for c in contour_map:
                            con, side = contour_map[c]
                            self.clist_final.append(con)
                            draw_text(img, c, contour_centroid(con), 1.5, (0, 0, 0), 3)
                            self.glyph_dict[c].contour = con
                            self.glyph_dict[c].visible = True
                    # complementary glyph not found. go thru each region and find the contour with the smallest error
                    else:
                        for region in side_regions:
                            if len(side_regions[region].contours) > 0:
                                print("adsfasdf")
                                err, contour, glyph = float("inf"), None, ""
                                for g in glyphs:
                                    side_regions[region].contours = list(sorted(side_regions[region].contours, key=lambda x : error(x, g)))
                                    best_contour = side_regions[region].contours[0]
                                    e = error(best_contour, g)
                                    print(e)
                                    if e < err:
                                        err = e
                                        contour = best_contour
                                        glyph = g
                                if err < self.options[glyph + '_error_high']:
                                    self.glyph_dict[glyph].visible = True
                                    self.glyph_dict[glyph].contour = contour
                                    self.clist_final.append(contour)
                                    self.clist_draw[glyph] = contour_centroid(contour)
                                    glyphs.remove(glyph)
        generate2()

        for g in self.glyph_dict:
            glyph = self.glyph_dict[g]
            if glyph.visible == True:
                pass
                # print(g)
                print(g + ": " + str(error(glyph.contour, g)))
        print()
    
    def shm(self):
        for g in self.glyph_dict:
            glyph_shm = name_to_shm(g)
            results = glyph_shm.get()
            glyph = self.glyph_dict[g]
            if glyph.visible:
                results.center_x, results.center_y = self.normalized(contour_centroid(glyph.contour))
                results.area = contour_area(glyph.contour)
                results.visible = 1
            else:
                # print("not visible")
                results.visible = 0
            glyph_shm.set(results)
        pass

if __name__ == '__main__':
    GlyphVision("forward", options=module_options,
               filters=filters_list)()
