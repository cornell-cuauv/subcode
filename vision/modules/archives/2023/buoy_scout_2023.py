#!/usr/bin/env python3

import numpy as np
import os
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


PICKLE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/ODJ_Vision/objects_2023/pickles/"

filters_list = [
    (lambda x: False if contour_area(x) == 0 else 3.1415926 * min_enclosing_circle(x)[1]**2 / (contour_area(x)) < 10)
]

glyph_list = ["wishbone", "nozzle", "dipper", "faucet"]

group_a = ["faucet", "dipper"]
group_b = ["wishbone", "nozzle"]

module_options = [
    options.BoolOption('use otsu', False),
    options.BoolOption('use canny', True),
    options.BoolOption('use canny dark', False),
    
    options.IntOption('close', 3, 0, 21),
    options.IntOption('dilation', 1, 0, 21),
    options.IntOption('max', 65, 0, 255),

    options.IntOption('lower', 120, 0, 255), # 107
    options.IntOption('upper', 220, 0, 255), # 255

    options.IntOption('faucet_error', 3, 0, 500),
    options.IntOption('dipper_error', 2, 0, 500),
    options.IntOption('nozzle_error', 4, 0, 500),
    options.IntOption('wishbone_error', 6, 0, 500),

    options.IntOption('faucet_error_high', 4, 0, 500),
    options.IntOption('dipper_error_high', 3, 0, 500),
    options.IntOption('nozzle_error_high', 5, 0, 500),
    options.IntOption('wishbone_error_high', 6, 0, 500)
]

# for g in glyph_list:
#     module_options.append(options.IntOption(g + "_error", 3, 0, 255))

class Glyph():
    """
    A Glyph represents the abstract glyph we are trying to find. It may be
    visible in the camera, in which we associate a contour with this Glyph
    object, or it is not, in which there is no association.
    """
    def __init__(self, strn):
        with open(PICKLE_DIR + strn + '.pickle', 'rb') as f:
            self.reference_contour = pickle.load(f)
            self.moments = cv2.moments(self.reference_contour)
            self.reference_hu_moments = cv2.HuMoments(self.moments)
            self.name = strn
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
        if in_circle(self.center, self.radius, min_enclosing_circle(contour)[0]):
            self.contours.append(contour)
            return True
        return False
    
    def draw(self, img, thickness):
        draw_circle(img, self.center, self.radius, self.color, thickness)

class ContourMoments():
    """
    A contour moment contains the hu_moment of a certain contour.
    """
    def __init__(self, contour):
        moments = cv2.moments(contour)
        self.hu_moments = cv2.HuMoments(moments)

class Buoy():
    """
    Represents the entire buoy.
    """
    def __init__(self, tl, tr, bl, br):
        """Creates an already processed Buoy."""
        self.found = True
        self.top_left = tl
        self.top_right = tr
        self.bottom_left = bl
        self.bottom_right = br
        

    def __init__(self):
        """Creates an empty Buoy."""
        self.found = False
        self.top_left = self.top_right = self.bottom_left = self.bottom_right = ""

    def set(self, tl, tr, bl, br):
        """Sets each parameter to a particular glyph."""
        self.top_left = tl
        self.top_right = tr
        self.bottom_left = bl
        self.bottom_right = br
        pass

class GlyphScout(VisionProcessBase):
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

    contour_corners = {}
    """
    Maps each contour to a corner.
    """

    glyph_frequencies = {
        "wishbone": { 1:0, 2:0, 3:0, 4:0 },
        "nozzle":   { 1:0, 2:0, 3:0, 4:0 },
        "dipper":   { 1:0, 2:0, 3:0, 4:0 },
        "faucet":   { 1:0, 2:0, 3:0, 4:0 }
    }
    
    frames = 0; threshold = 15
    """
    Number of frames logged.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.all_four = False
        self.filters.append((lambda x: self.con_area(x) >= 0.02))
        for g in glyph_list:
            self.glyph_dict[g] = Glyph(g)
        self.reset_shm()

    def reset_shm(self):
        for g in glyph_list:
            results = name_to_shm(g).get()
            results.heuristic = 0
            results.visible = 0
            results.error = 0
            name_to_shm(g).set(results)
    def color_filter(self, img):   
        self.post('original', img)

        gray, _ = bgr_to_gray(img)
        if self.options['use otsu']:
            _, threshed = otsu_threshold(gray)
            threshed = ~threshed
        elif self.options['use canny']:
            threshed = canny(gray, self.options['lower'], self.options['upper'])
        elif self.options['use canny dark']:
            threshed1 = canny(gray, self.options['lower'], self.options['upper'])
            threshed2 = range_threshold(gray, 0, self.options['max'])
            threshed = threshed1 | threshed2
        else:
            threshed = range_threshold(gray, 0, self.options['max'])
        threshed = morph_close_holes(threshed, elliptic_kernel(self.options['close']))
        threshed = dilate(threshed, elliptic_kernel(self.options['dilation']))
        self.post('threshed', threshed)
        self.clist = all_contours(threshed)

    def shape_filter(self):
        """
        Filters contours based on certain filter functions.

        Effect: clist may be filtered.
        """
        for f in self.filters:
            self.clist = list(filter(f, self.clist))
    
    def higher_process(self, img):       
        h, w, _ = img.shape
        print("height", str(h))
        print("height", str(w))
        for g in self.glyph_dict:
            self.glyph_dict[g].visible= False
        # store contours and their moments for rapid lookup
        self.glyph_moments = {}
        self.contour_corners = {}
        self.all_four = False
        for c in self.clist:
            self.glyph_moments[contour_centroid(c)] = ContourMoments(c)
        
        def error(contour, target):
            """
            Calculates error of hu moment of [contour] with respect to [target].
            contour : the contour being """
            result = 0
            def transform(num):
                return abs(num)
            
            cm = self.glyph_moments[contour_centroid(contour)]
            hu_moments = cm.hu_moments
            index = 0
            result = 1
            for ref_moment, moment in zip(self.glyph_dict[target].reference_hu_moments, hu_moments):
                if index < 7:
                    trm = transform(ref_moment)
                    tm = transform(moment)
                    result *= abs(max(trm, tm) / min(trm, tm))
                index += 1
                # result += abs(max(ref_moment, moment)) / abs(min(ref_moment, moment))
                # result += (ref_moment - moment) ** 2
            result = math.log10(result)
            return result
        
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
                        x, y = min_enclosing_circle(c)[0]
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
                        # side_regions[c].draw(img, 3)
                        for contour in self.clist:
                            side_regions[c].add_if_contains(contour)
                        # draw_text(img, str(len(side_regions[c].contours)), side_regions[c].center, 2, (255, 0, 0), 3)
                        
                    diag_regions = {
                        "top_left"      : Region((x - diag_dist, y - diag_dist), diag_r, (0, 0, 255)),
                        "top_right"     : Region((x + diag_dist, y - diag_dist), diag_r, (0, 0, 255)),
                        "bottom_left"   : Region((x - diag_dist, y + diag_dist), diag_r, (0, 0, 255)),
                        "bottom_right"  : Region((x + diag_dist, y + diag_dist), diag_r, (0, 0, 255))
                    }

                    for c in diag_regions:
                        # diag_regions[c].draw(img, 3)
                        for contour in self.clist:
                            diag_regions[c].add_if_contains(contour)
                        # draw_text(img, str(len(diag_regions[c].contours)), diag_regions[c].center, 2, (0, 0, 255), 3)

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
                        # diag_regions[reg].draw(img, 15)

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
                            pass
                            # side_regions[region].draw(img, 15)
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
        def print_results():
            for g in self.glyph_dict:
                glyph = self.glyph_dict[g]
                if glyph.visible == True:
                    pass
                    # print(g)
                    print(g + ": " + str(error(glyph.contour, g)))
                else:
                    print(g + ": not visible")
            print()
        def extract_corners():
            num_visible = 0
            for g in self.glyph_dict:
                if self.glyph_dict[g].visible:
                    num_visible += 1
            if num_visible == 4: # we consider them when we see all four
                self.all_four = True
                # 1: top left     2: top right       3: bottom left       4: bottom right
                list_of_contours = list(self.glyph_dict.values())
                # sort by ascending x coordinate
                list_of_contours = list(sorted(list_of_contours, key=lambda x: contour_centroid(x.contour)[0]))           
                left, right = list_of_contours[:2], list_of_contours[2:]

                # sort by ascending y coordinate
                left = list(sorted(left, key=lambda x: contour_centroid(x.contour)[1]))
                right = list(sorted(right, key=lambda x: contour_centroid(x.contour)[1]))  

                top_left, bottom_left = left[0].contour, left[1].contour
                top_right, bottom_right = right[0].contour, right[1].contour

                self.contour_corners = {
                    contour_centroid(top_left) : 1,
                    contour_centroid(top_right) : 2,
                    contour_centroid(bottom_left) : 3,
                    contour_centroid(bottom_right) : 4,
                }

                self.frames += 1
                pass
            pass
        
        if self.threshold < 0:
            print("hi")
            self.all_four = True
            pass
        else:
            generate2()
            print_results()
            if self.frames < self.threshold:
                extract_corners()
                pass
    
    def shm(self):
        num = 0
        write_corners = False
        if self.threshold < 0:
            for g in self.glyph_dict:
                glyph_shm = name_to_shm(g)
                results = glyph_shm.get()
                number, freq = 0, -1
                freq_list = self.glyph_frequencies[self.glyph_dict[g].name]
                for n in freq_list:
                    if freq_list[n] > freq:
                        number = n
                        freq = freq_list[n]
                results.heuristic = number
                glyph_shm.set(results)
            return
        
        for g in self.glyph_dict:
            glyph_shm = name_to_shm(g)
            results = glyph_shm.get()
            glyph = self.glyph_dict[g]
            if self.frames < self.threshold:
                results.heuristic = 0
            if glyph.visible:
                results.center_x, results.center_y = self.normalized(contour_centroid(glyph.contour))
                results.area = self.con_area(glyph.contour)
                if self.all_four:
                    
                    num = self.contour_corners[contour_centroid(self.glyph_dict[g].contour)]
                    print("->", self.glyph_dict[g].name, '->', num)
                    self.glyph_frequencies[self.glyph_dict[g].name][num] += 1
                    if self.frames >= self.threshold:
                        write_corners = True
                        number, freq = 0, -1
                        freq_list = self.glyph_frequencies[self.glyph_dict[g].name]
                        for n in freq_list:
                            if freq_list[n] > freq:
                                number = n
                                freq = freq_list[n]
                        results.heuristic = number
            else:
                # print("not visible")
                results.visible = 0
            glyph_shm.set(results)
        if write_corners:  
                self.frames += 1
        print(self.glyph_frequencies)
        pass

    def con_area(self, con):
        _, radius = min_enclosing_circle(con)
        area = 3.14159 * radius ** 2
        return self.normalized_size(area)
        

if __name__ == '__main__':
    GlyphScout("forward", options=module_options,
               filters=filters_list)()
