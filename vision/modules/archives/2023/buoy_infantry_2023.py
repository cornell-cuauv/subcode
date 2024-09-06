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
    (lambda x: False if contour_area(x) == 0 else 3.1415926 * min_enclosing_circle(x)[1]**2 / (contour_area(x)) < 10), 
]

module_options = [
    options.BoolOption('use otsu', False), # Method option
    options.BoolOption('use canny', True),
    options.BoolOption('use canny dark', False),

    options.IntOption('max', 65, 0, 255), # Lightness threshold

    options.IntOption('lower', 120, 0, 255), # Canny edge detection parameters # 200
    options.IntOption('upper', 220, 0, 255), # 255

    options.IntOption('close', 3, 0, 21),
    options.IntOption('dilation', 1, 0, 21),

    options.IntOption('faucet_error', 4, 0, 500), #6    # Error caps for each glyph
    options.IntOption('dipper_error', 2, 0, 500), #2
    options.IntOption('nozzle_error', 4, 0, 500), #6
    options.IntOption('wishbone_error', 3, 0, 500), #4
]

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
    
    def in_region(self, contour):
        return in_circle(self.center, self.radius, contour_centroid(contour))
    
    def add_if_contains(self, contour):
        if self.in_region(contour):
            self.contours.append(contour)

    
    def draw(self, img, thickness):
        draw_circle(img, self.center, self.radius, self.color, thickness)

class GlyphInfantry(VisionProcessBase):
    """
    Indicates whether the orientation of the glyphs on the buoy is known.
    """

    names = ["faucet", "wishbone", "nozzle", "dipper"]
    """ The names of each glyph. """

    reference_moments = {}
    """ Maps each glyph name to its reference hu_moment. """

    last_frame_reference_moments = {}
    """The last frame's capture contour moments. """

    contour_moments = {}
    """
    Maps each contour to its hu_moment. Since contour objects are non-hashable,
    we use the contour centroid, because each contour centroid is a reasonably
    distinct attribute between different contours.
    """

    contours = []
    """
    List of contours that are identified to be a glyph, but we do not know which
    one it is quite yet.
    """
    
    found_glyphs = {}
    """ Maps a corner to an associated contour."""

    inferred_glyphs = {}
    """Maps a corner to an associated center, from inference if said corner was
    not found."""


    name_to_corner = {}
    corner_to_name = {}
    """ The orientation of the glyphs on the buoy. Will only be considered if
    orientation_known is True."""
    
    orientation_known = True
    """Indicates whether we know the orientation of the buoy."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters.append((lambda x: self.con_area(x) >= 0.02))
        for c in self.names:
            with open(PICKLE_DIR + c + '.pickle', 'rb') as f:
              reference_contour = pickle.load(f)
              reference_hm = cv2.HuMoments(cv2.moments(reference_contour))
              self.reference_moments[c] = reference_hm
        self.last_frame_reference_moments = self.reference_moments.copy()
            

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
                self.post("darkness", threshed2)
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

    ##########################################################
    #                    HELPER FUNCTIONS                    #
    # ------------------------------------------------------ #
    #   Simple building block functions that perform basic   #
    #   computations.                                        #
    ##########################################################

    def error(self, contour, target):
            """
            Calculates error of hu moment of [contour] with respect to [target].
            contour : the contour being """
            result = 0
            def transform(num):
                return abs(num)
            
            hu_moments = self.contour_moments[contour_centroid(contour)]
            index = 0
            result = 1
            for ref_moment, moment in zip(self.reference_moments[target], hu_moments):
                if index < 7:
                    trm = transform(ref_moment)
                    tm = transform(moment)
                    result *= abs(max(trm, tm) / min(trm, tm))
                index += 1
                # result += abs(max(ref_moment, moment)) / abs(min(ref_moment, moment))
                # result += (ref_moment - moment) ** 2
            result = math.log10(result)
            return result
    
    def opposite_glyph_name(self, name):
        """
        Returns the name of the glyph diagonal to [name].
        """
        opp_region = self.get_opposite(self.name_to_corner[name])
        return self.corner_to_name[opp_region]

    def hu_moment(self, contour):
        """
        Returns the hu_moment of a specified contour or glyph name.
        """
        if isinstance(contour, str): # reference glyph
            return self.reference_moments[contour]
        return self.contour_moments[contour_centroid(contour)] # contour
    
    def min_error(self, target_list, contours, lenient=False, ignore=False):
        """
        Given a list of targets, we go through each contour and see which match
        of contour - reference yields the lowest error. Must also pass the
        specified error threshold.
        
        Returns a dictionary with the error, glyph_name, and contour if a match
        is found, otherwise returns None.
        """
        if len(contours) > 0:
            err, best, con = float("inf"), None, None
            for glyph in target_list:
                contours_sorted = list(sorted(contours, key=lambda x: self.error(x, glyph)))
                best_contour = contours_sorted[0]
                e = self.error(best_contour, glyph)
                threshold = self.options[glyph + "_error"]
                if lenient:
                    threshold *= 3
                if ignore:
                    threshold = float("inf")
                if e < threshold and e < err:
                    err = e
                    best = glyph
                    con = best_contour
            if best is not None:
                return {"error": err, "glyph_name": best, "contour": con}
        return None

    def get_opposite(self, string):
        if string == 'TL':
            return 'BR'
        elif string == 'TR':
            return 'BL'
        elif string == 'BL':
            return 'TR'
        elif string == 'BR':
            return 'TL'
        
    def get_adjacent(self, string):
        if string == 'TL':
            return ['T', 'L']
        elif string == 'TR':
            return ['T', 'R']
        elif string == 'BL':
            return ['B', 'L']
        elif string == 'BR':
            return ['B', 'R']

    def con_area(self, con):
        _, radius = min_enclosing_circle(con)
        area = 3.14159 * radius ** 2
        return self.normalized_size(area)
    
    ##########################################################
    #                    BASIC ALGORITHMS                    #
    # ------------------------------------------------------ #
    #   Smaller algorithms that are part of the higher       #
    #   processing.                                          #
    ##########################################################

    def memoize(self):
        """
        Reinitialize all values that need to be reset.
        Creates the hu_moments of each contour on the map.
        """
        self.contour_moments = {}
        self.found_glyphs = {}
        self.contours = []
        self.inferred_glyphs = {}
        for c in self.clist:
            self.contour_moments[contour_centroid(c)] = cv2.HuMoments(cv2.moments(c))
    
    def detect_first_glyph(self):
        """
        Given the set of contours and their hu_moments, as well as four
        reference hu_moments, find the most likely match of contour + reference.
        
        If no match is found, then we assume the buoy is not visible.

        Effect: either no match is found in which there is no effect, or a match
        is found, and we place this glyph_name:contour pair into found_glyphs
        
        Returns: True if a match is found.
        """
        results = self.min_error(self.names, self.clist)
        if results is not None:
          self.contours.append(results['contour'])
          self.clist_final.append(results['contour'])
          return True
        return False
    
    def localize(self, img):
        """
        Given that we have found one glyph_name:contour match, we run the four
        corner algorithm. First, we lookup the orientation of the found corner,
        then look specifically in the opposite corner of that one.
        
        Effect: we find a match with the complementary glyph with small error,
        then we add this glyph_name:contour pair into found glyphs.

        Returns: True if a match is found.
        """
        
        con = self.contours[0]
        (x, y), r = min_enclosing_circle(con)
        diag_dist = int(2.4 * r);   diag_r = int(10/7 * r)
        side_dist = int(2.05*r);     side_r = int(10/8 * r)
        x, y = int(x), int(y)

        diag_regions = {
            "TL"  : Region((x - diag_dist, y - diag_dist), diag_r, (0, 0, 255)),
            "TR"  : Region((x + diag_dist, y - diag_dist), diag_r, (0, 0, 255)),
            "BL"  : Region((x - diag_dist, y + diag_dist), diag_r, (0, 0, 255)),
            "BR"  : Region((x + diag_dist, y + diag_dist), diag_r, (0, 0, 255))  }

        for c in diag_regions:
            # diag_regions[c].draw(img, 3)
            for contour in self.clist:
                if self.min_error(self.names, [contour]) is not None:
                    diag_regions[c].add_if_contains(contour)
            
            # draw_text(img, str(len(diag_regions[c].contours)), diag_regions[c].center, 2, (0, 0, 255), 3)
        
        side_regions = {
            "T"   : Region((x, y - side_dist), side_r, (255, 0, 0)),
            "B"   : Region((x, y + side_dist), side_r, (255, 0, 0)),
            "L"   : Region((x - side_dist, y), side_r, (255, 0, 0)),
            "R"   : Region((x + side_dist, y), side_r, (255, 0, 0))  }

        for c in side_regions:
            # side_regions[c].draw(img, 3)
            for contour in self.clist:
                if self.min_error(self.names, [contour]) is not None:
                    side_regions[c].add_if_contains(contour)
            # draw_text(img, str(len(side_regions[c].contours)), side_regions[c].center, 2, (255, 0, 0), 3)

        the_corner = ""
        num = 0
        
        for corner in diag_regions:
            sum = 1 if len(diag_regions[corner].contours) > 0 else 0
            adjacent_sides = self.get_adjacent(corner)
            for side in adjacent_sides:
                if len(side_regions[side].contours) > 0:
                    sum += 1
            if sum > num:
                num = sum
                the_corner = corner
            pass

        # process considered regions
        side = {}
        if the_corner == "TL":
            side['T'] = "TR"
            side['L'] = "BL"
        elif the_corner == "TR":
            side['T'] = "TL"
            side['R'] = "BR"
        elif the_corner == "BL":
            side['B'] = "BR"
            side['L'] = "TL"
        elif the_corner == "BR":
            side['B'] = "BL"
            side['R'] = "TR"

        if num == 3: # all four found.
            # print("3 +1")
            results = self.min_error([self.corner_to_name[the_corner]], diag_regions[the_corner].contours, lenient=True)
            if results is not None:
                self.found_glyphs[the_corner] = results['contour']
        
            opp_corner = self.get_opposite(the_corner)
            self.found_glyphs[opp_corner] = self.contours[0]
            
            for key in self.get_adjacent(the_corner):
                results = self.min_error([self.corner_to_name[side[key]]], side_regions[key].contours, lenient=True)
                if results is not None:
                    self.found_glyphs[side[key]] = results['contour']

        elif num == 2: # three of four.
            # print("2 +1")
            if len(diag_regions[the_corner].contours) == 0: # case 1: corner piece is not found, so the other two pieces are there
                opp_corner = self.get_opposite(the_corner)
                self.found_glyphs[opp_corner] = self.contours[0]
                
                for key in self.get_adjacent(the_corner):
                    results = self.min_error([self.corner_to_name[side[key]]], side_regions[key].contours, lenient=True)
                    if results is not None:
                        self.found_glyphs[side[key]] = results['contour']
            else: # case 2: corner piece is found, so one of two side pieces are missing
                opp_corner = self.get_opposite(the_corner)
                self.found_glyphs[opp_corner] = self.contours[0]
                results = self.min_error([self.corner_to_name[the_corner]], diag_regions[the_corner].contours, lenient=True)
                if results is not None:
                    self.found_glyphs[the_corner] = results['contour']
                for key in self.get_adjacent(the_corner):
                    if len(side_regions[key].contours) > 0:
                        results = self.min_error([self.corner_to_name[side[key]]], side_regions[key].contours, lenient=True)
                        if results is not None:
                            self.found_glyphs[side[key]] = results['contour']
        
        elif num == 1: # two of four.
            side = ""
            diag_one = False
            for key in diag_regions:
                if len(diag_regions[key].contours) > 0:
                    side = key
                    diag_one = True
            if not diag_one:
                for key in side_regions:
                    if len(side_regions[key].contours) > 0:
                        side = key

            if diag_one: # case 1: diagonal
                results = self.min_error([self.corner_to_name[the_corner]], diag_regions[the_corner].contours, lenient=True)
                if results is not None:
                    self.found_glyphs[the_corner] = results['contour']
                
                opp_corner = self.get_opposite(the_corner)
                self.found_glyphs[opp_corner] = self.contours[0]
                pass
            else: # case 2: sides. four subcases
                two_cases = [] # two subsubcases...
                if side == "L":
                    two_cases = [{"orig": "TR", "side": "TL"}, {"orig": "BR", "side": "BL"}]
                elif side == "R":
                    two_cases = [{"orig": "TL", "side": "TR"}, {"orig": "BL", "side": "BR"}]
                elif side == "T":
                    two_cases = [{"orig": "BR", "side": "TR"}, {"orig": "BL", "side": "TL"}]
                elif side == "B":
                    two_cases = [{"orig": "TR", "side": "BR"}, {"orig": "TL", "side": "BL"}]
                pass
                error = float("inf")
                right_case = []
                other_contour = None
                for case in two_cases:
                    side_results = self.min_error([self.corner_to_name[case["side"]]], side_regions[side].contours, lenient=True)
                    orig_results = self.min_error([self.corner_to_name[case["orig"]]], self.contours, lenient=True)
                    
                    if side_results is not None and orig_results is not None:
                        # print(side_results['glyph_name'], side_results['error'])
                        # print(orig_results['glyph_name'], orig_results['error'])
                        e = orig_results['error']**2 + side_results['error']**2
                        if e < error:
                            error = e
                            right_case = case
                            other_contour = side_results['contour'] 
                if other_contour is not None:
                    self.found_glyphs[right_case['orig']] = self.contours[0]
                    self.found_glyphs[right_case['side']] = other_contour
            print("1 +1")
        else: # lone one.
            print("0 +1")
            results = self.min_error(self.names, self.contours, lenient=True)
            if results is not None:
                print(results['error'])
                self.found_glyphs[self.name_to_corner[results['glyph_name']]] = results['contour']

    def infer(self):
        all_corners = ['TL', 'TR', 'BL', 'BR']
        found_corners = list(self.found_glyphs.keys())
        unfound_corners = [x for x in all_corners if x not in found_corners]

        if len(unfound_corners) == 1: # close the remaining corner
            map = {'TL': ('BL', 'TR'),  'TR': ('BR', 'TL'),
                   'BR': ('TR', 'BL'),  'BL': ('TL', 'BR')}
            assignment = map[unfound_corners[0]]
            self.inferred_glyphs[unfound_corners[0]] = min_enclosing_circle(self.found_glyphs[assignment[0]])[0][0], min_enclosing_circle(self.found_glyphs[assignment[1]])[0][1]
        elif len(unfound_corners) == 2: # two corners, or two sides
            pair = [unfound_corners[0], unfound_corners[1]]
            pair = tuple(sorted(pair))
            print(pair)
            if pair == ('BR', 'TL') or pair == ('BL', 'TR'): # two corners
                print("here")
                map = { ('BR', 'TL'): ('TR', 'BL'), 
                        ('BL', 'TR'): ('TL', 'BR') }
                fst, snd = pair
                assignment = map[pair]
                self.inferred_glyphs[fst] = min_enclosing_circle(self.found_glyphs[assignment[0]])[0][0], min_enclosing_circle(self.found_glyphs[assignment[1]])[0][1]
                self.inferred_glyphs[snd] = min_enclosing_circle(self.found_glyphs[assignment[1]])[0][0], min_enclosing_circle(self.found_glyphs[assignment[0]])[0][1]
            else: # two sides
                if pair == ('BL', 'BR'):
                    (x1, y1), r1 = min_enclosing_circle(self.found_glyphs['TL'])
                    (x2, y2), r2 = min_enclosing_circle(self.found_glyphs['TR'])
                    radius = (r1 + r2)
                    self.inferred_glyphs['BL'] = (x1, y1 + radius)
                    self.inferred_glyphs['BR'] = (x2, y2 + radius)
                    pass
                elif pair == ('BL', 'TL'):
                    (x1, y1), r1 = min_enclosing_circle(self.found_glyphs['BR'])
                    (x2, y2), r2 = min_enclosing_circle(self.found_glyphs['TR'])
                    radius = (r1 + r2)
                    self.inferred_glyphs['BL'] = (x1 - radius, y1)
                    self.inferred_glyphs['TL'] = (x2 - radius, y2)
                    pass
                elif pair == ('BR', 'TR'):
                    (x1, y1), r1 = min_enclosing_circle(self.found_glyphs['BL'])
                    (x2, y2), r2 = min_enclosing_circle(self.found_glyphs['TL'])
                    radius = (r1 + r2)
                    self.inferred_glyphs['BR'] = (x1 + radius, y1)
                    self.inferred_glyphs['TR'] = (x2 + radius, y2)
                    pass
                elif pair == ('TL', 'TR'):
                    (x1, y1), r1 = min_enclosing_circle(self.found_glyphs['BL'])
                    (x2, y2), r2 = min_enclosing_circle(self.found_glyphs['BR'])
                    radius = (r1 + r2)
                    self.inferred_glyphs['TL'] = (x1, y1 - radius)
                    self.inferred_glyphs['TR'] = (x2, y2 - radius)
                    pass
            pass
        # ignore if 3 or 4
        pass

    def fetch_mapping(self):
        dipper = shm.dipper_glyph
        if dipper.heuristic.get() == 0:
            print("mapping not found yet")
            return
        else:
            num_corner_map = {1: "TL", 2: "TR", 3: "BL", 4: "BR"}
            glyph_corner_map = {}
            corner_glyph_map = {}
            for x in self.names:
                glyph_corner_map[x] = num_corner_map[int(name_to_shm(x).heuristic.get())]
            pass
            for x in glyph_corner_map:
                corner_glyph_map[glyph_corner_map[x]] = x
            self.name_to_corner = glyph_corner_map
            self.corner_to_name = corner_glyph_map
        pass

    def create_drawings(self, img):
        for key in self.found_glyphs:
            # print(key, ": ", self.error(self.found_glyphs[key], key))
            x, y = min_enclosing_circle(self.found_glyphs[key])[0]
            self.clist_draw[self.corner_to_name[key]] = int(x), int(y)
            self.clist_final.append(self.found_glyphs[key])
        
        for key in self.inferred_glyphs:
            x, y = self.inferred_glyphs[key]
            x, y = int(x), int(y)
            self.clist_draw[self.corner_to_name[key] + "(inf)"] = x, y
            draw_circle(img, (x, y), 30, (255, 255, 0), -1)
    
    def print_sizes(self):
        print("reference_moments", str(len(self.reference_moments.keys())))
        print("lf_ref_moments", str(len(self.last_frame_reference_moments.keys())))
        print("contour_moments", str(len(self.contour_moments.keys())))
        print("contours", len(self.contours))
        print("inferred_glyphs", len(self.inferred_glyphs.keys()))
        print("name_to_corner", len(self.name_to_corner.keys()))
        print("corner_to_name", len(self.corner_to_name.keys()))
    ######################################################
    #                 THE HUGE ALGORITHM                 #
    ######################################################
    
    def higher_process(self, img):
        for con in self.clist:
            x, y = min_enclosing_circle(con)[0]
            x, y = int(x), int(y)
            draw_circle(img, (x, y), 2, (255, 255, 0))
        if self.name_to_corner != {}: # nonempty
            self.memoize()
            first_found = self.detect_first_glyph()
            if first_found:
                self.localize(img)
                self.infer()
                self.create_drawings(img)
        else:
            self.fetch_mapping()
        self.print_sizes()
    
    def shm(self):

        all_glyphs = ['faucet', 'dipper', 'wishbone', 'nozzle']
        area = 0
        num_glyphs = 0
        for g in self.found_glyphs:
            glyph = self.corner_to_name[g]
            all_glyphs.remove(glyph)

            glyph_shm = name_to_shm(glyph)
            results = glyph_shm.get()
            contour = self.found_glyphs[g]
            results.center_x, results.center_y = self.normalized(min_enclosing_circle(contour)[0])
            results.area = self.con_area(contour)

            area += self.con_area(contour)
            num_glyphs += 1

            results.visible = 1
            results.error = 0

            glyph_shm.set(results)

        average_area = 0
        if num_glyphs > 0:
            average_area = area / num_glyphs

        for g in self.inferred_glyphs:
            glyph = self.corner_to_name[g]
            all_glyphs.remove(glyph)

            glyph_shm = name_to_shm(glyph)
            results = glyph_shm.get()

            results.center_x, results.center_y = self.normalized(self.inferred_glyphs[g])
            results.area = average_area

            results.visible = 1
            results.error = 0.5

            glyph_shm.set(results)
        
        for glyph in all_glyphs:
            glyph_shm = name_to_shm(glyph)
            results = glyph_shm.get()
            results.visible = 0
            glyph_shm.set(results)

        pass
    
if __name__ == '__main__':
    GlyphInfantry("forward", options=module_options,
               filters=filters_list)()
