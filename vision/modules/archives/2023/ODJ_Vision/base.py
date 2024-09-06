#!/usr/bin/env python3
from vision.framework.feature import outer_contours, contour_area, min_enclosing_rect
from vision.framework.transform import elliptic_kernel, morph_remove_noise, morph_close_holes
from vision.framework.color import thresh_color_distance, bgr_to_lab
from vision import options
from vision.modules.base import ModuleBase
from vision.framework.draw import draw_contours, draw_text, draw_circle

import cv2
import numpy as np

module_options = [
]

filters_list = [
]


class VisionProcessBase(ModuleBase):
    """A structured model for how images should be processed into data.
    Image to contour to shm follows the process below:

    Img |> color filter |> feature filters |> higher processing |> post to shm/webgui

    Color filter: thresh_color_distance to get contours around the color of
    the object of interest.

    Feature filters: certain features of each contour are filtered in/out
    to reduce the number of contours. Removes contours that have similar color
    but do not resemble the object of interest.

    Higher processing: additional features to look out for. Unique for each
    object."""

    is_visible = True
    """Represents if the object to be detected is visible. """

    clist = []
    """A list of contours that pass the color and feature filters. """

    clist_final = []
    """A list of final contours. """

    clist_draw = {}
    """A list of labels that maps string -> coordinate (x, y) to be drawn to the webgui. """

    def __init__(self, default_directions=None, options=None, order_post_by_time=True, filters=[]):
        self.filters = filters

        """A list of features that describe a contour that would represent the object. """
        super().__init__(default_directions, options, order_post_by_time)

    def process(self, img):
        """
        Streamlines the vision process.
        """
        self.clist, self.clist_final, self.clist_draw = [], [], {}
        self.color_filter(img)
        self.shape_filter()
        self.higher_process(img)
        self.shm()
        self.draw(img)
        self.post("final", img)

    def color_filter(self, img):
        """
        Creates contours for a certain color range.

        Effect: contour list now has contour values.
        """
        lab, lab_split = bgr_to_lab(img)
        self.post("lab", lab)

        def option(str):
            return self.options[str]

        # thresh_color_distance
        threshed, _ = thresh_color_distance(lab_split, (0, option(
            'a'), option('b')), option('dist'), ignore_channels=[0])

        # removes noise, then closes holes
        threshed = morph_close_holes(morph_remove_noise(threshed,
                                                        elliptic_kernel(option('thresh'))), elliptic_kernel(option('thresh')))
        self.post("threshed", threshed)
        self.clist = outer_contours(threshed)

    def shape_filter(self):
        """
        Filters contours based on certain filter functions.

        Effect: clist may be filtered.
        """
        for f in self.filters:
            self.clist = list(filter(f, self.clist))

    def higher_process(self):
        """
        Determines whether a contour has been found in the contour list.
        Places confirmed contours in [clist_final]. Does not have to be removed
        from the original [clist].

        Effect: clist_final may have confirmed contours.
        Effect: self.is_visible is updated.
        """

    def shm(self):
        """
        Adds values to shm based on contouring and filtering results.
        Requires: is_visible, and clist_final has values.
        """

    def draw(self, img):
        """
        Draws to webgui.
        """
        draw_contours(img, self.clist, (255, 0, 255),
                      2)  # contours past filters are considered
        # contours past higher processing are green
        draw_contours(img, self.clist_final, (128, 255, 128), 5)
        for key in self.clist_draw.keys():
            x, y = self.clist_draw.get(key)
            draw_circle(img, (x, y), 2, (255, 255, 255), 2)
            draw_text(img, key, (x+10, y+10), 1, (0, 0, 0), 2)
        
        #size of contour points
        # if len(self.clist_final) > 0:
        #     #concatinate poits form all shapes into one array
        #     cont = np.vstack(self.clist_final)
        #     hull = cv2.convexHull(cont)
        #     uni_hull = []
        #     uni_hull.append(hull) # <- array as first element of list
        #     cv2.drawContours(img,uni_hull,-1,255,2)

        # draw_contours(img, ctr, (255, 255, 128), 3)


if __name__ == '__main__':
    VisionProcessBase("forward", options=module_options,
                      filters=filters_list)()
