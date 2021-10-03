#!/usr/bin/env python3
 
from collections import namedtuple, OrderedDict
 
import shm
 
from vision.modules.base import ModuleBase
from vision import options
 
from vision.framework.color import bgr_to_lab, thresh_color_distance
from vision.framework.transform import rect_kernel, morph_remove_noise
from vision.framework.feature import outer_contours, contour_centroid, contour_area
from vision.framework.draw import draw_contours
 
Buoy = namedtuple('Buoy',
                  ('shm_group', 'color', 'color_defaults', 'threshold_default'))
 
buoys = OrderedDict()
buoys['red'] = Buoy(shm.red_buoy_results, (0, 0, 255), (0, 177, 158), 46)
buoys['green'] = Buoy(shm.green_buoy_results, (0, 255, 0), (0, 51, 194), 40)
buoys['yellow'] = Buoy(shm.yellow_buoy_results, (0, 255, 255), (0, 112, 219), 40)
 
channels = ['lab_l', 'lab_a', 'lab_b']
 
module_options = []
 
def buoy_color_opt(buoy_name, channel_num):
    return '{}_{}'.format(buoy_name, channels[channel_num])
 
def buoy_thresh_opt(buoy_name):
    return '{}_threshold'.format(buoy_name)
 
module_options.append(options.BoolOption('debug', False))
 
for buoy_name, buoy in buoys.items():
    for channel_num, _ in enumerate(channels):
        module_options.append(
            options.IntOption(buoy_color_opt(buoy_name, channel_num),
                              buoy.color_defaults[channel_num], 0, 255))
    module_options.append(
        options.DoubleOption(buoy_thresh_opt(buoy_name),
                             buoy.threshold_default, 0, 255))
 
kernel = rect_kernel(5)
 
class BuoysSim(ModuleBase):
    def process(self, img):
        debug = self.options['debug']
 
        lab, lab_split = bgr_to_lab(img)
 
        if debug:
            self.post('lab', lab)
 
        for buoy_name, buoy in buoys.items():
            color_target = [self.options[buoy_color_opt(buoy_name, channel_num)]
                            for channel_num, _ in enumerate(channels)]
            thresh = self.options[buoy_thresh_opt(buoy_name)]
            threshed_lab, lab_dist = thresh_color_distance(
                lab_split, color_target, thresh, ignore_channels=[0])
 
            if debug:
                self.post('{}_threshed'.format(buoy_name), threshed_lab)
                self.post('{}_dist'.format(buoy_name), lab_dist)
 
            denoised = morph_remove_noise(threshed_lab, kernel)
            contours = sorted(outer_contours(denoised), key=contour_area)
 
            group = buoy.shm_group.get()
 
            if len(contours) > 0 and contour_area(contours[-1]) > 50:
                buoy_contour = contours[-1]
 
                draw_contours(img, [buoy_contour], color=buoy.color, thickness=3)
 
                group.heuristic_score = 1
                group.center_x, group.center_y = \
                        self.normalized(contour_centroid(buoy_contour))
                group.area = contour_area(buoy_contour)
            else:
                group.heuristic_score = 0
                group.area = -1
 
            buoy.shm_group.set(group)
 
        self.post('output', img)
 
if __name__ == '__main__':
    BuoysSim('forward', module_options)()
