#!/usr/bin/env python3
from mission.framework.ssc256_consistency import ConsistentTargeting
from vision.modules.ODJ_Vision.base import VisionProcessBase
from vision import options
from vision.framework.feature import contour_area, min_enclosing_circle, contour_centroid, contour_approx
import shm
from vision.framework.color import thresh_color_distance, bgr_to_lab
from vision.framework.feature import outer_contours, contour_area, min_enclosing_rect
from vision.framework.transform import elliptic_kernel, morph_remove_noise, morph_close_holes
from vision.framework.color import range_threshold, thresh_color_distance, bgr_to_lab, bgr_to_gray
from vision import options
from vision.modules.base import ModuleBase
from vision.framework.draw import draw_contours, draw_text, draw_circle, draw_rot_rect, draw_arrow
import math

import cv2

module_options = [
    options.IntOption('a', 146, 0, 255),
    options.IntOption('b', 157, 0, 255),
    options.IntOption('c', 150, 0, 255),
    options.IntOption('dist', 25, 0, 50),
    options.IntOption('thresh', 1, 0, 10),
    options.IntOption('erode', 10, 1, 100),
    options.IntOption('erode_iter', 1, 1, 20),
    options.BoolOption("invert_thresh", False),
]


colors = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255), (170, 110, 40), (255, 250, 200), (128, 0, 0), (170, 255, 195), (128, 128, 0), (255, 215, 180), (0, 0, 128), (128, 128, 128), (255, 255, 255), (0, 0, 0)]

class OctagonChevronsVision(ModuleBase):
    consistency = ConsistentTargeting(20, 'pos', num_detections=4)

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

        threshed = morph_remove_noise(threshed, elliptic_kernel(option('erode')), iterations=option('erode_iter'))
        threshed = morph_close_holes(threshed, elliptic_kernel(option('erode')), iterations=option('erode_iter'))
        
        if self.options["invert_thresh"]:
            threshed = cv2.bitwise_not(threshed)
        
        self.post("threshed", threshed)

        return threshed

    def shape_filter(self, clist, filters):
        """
        Filters contours based on certain filter functions.

        Effect: clist may be filtered.
        """
        for f in filters:
            clist = list(filter(f, clist))

        return clist

    def process(self, img):

        # crop bottom of image
        # img = img[:-55,:]
        
        chevron_data = []
        threshed = self.color_filter(img)
        clist = outer_contours(threshed)

        def filter_rects(cnt, min_percent, max_percent):
            (center_x, center_y), (width, height), angle = min_enclosing_rect(cnt)
            if width > 0 and height > 0:
                return contour_area(cnt)/(width*height) > min_percent and contour_area(cnt)/(width*height) < max_percent
            else:
                return False
        
        filters_list = [
            (lambda x: contour_area(x) >= 500),
            (lambda x: filter_rects(x, 0.5, 1)),
        ]

        clist = self.shape_filter(clist, filters_list)


        for count, cnt in enumerate(clist):
            (center_x, center_y), (width, height), angle = min_enclosing_rect(cnt)

            if width > 0 and height > 0:
                
                # Angle should always be from long side of chevron
                if width > height:
                    angle += 90

                if angle > 90:
                    angle -= 180
                
                draw_arrow(img, (int(center_x), int(center_y)), (int(center_x + 2 * width * math.cos(math.radians(angle))), int(center_y + 2 * height * math.sin(math.radians(angle)))), (0, 0, 255), 10)
                
                norm_center_x, norm_center_y = self.normalized((center_x, center_y))

                data_dict = {
                    'norm_center_x': norm_center_x,
                    'norm_center_y': norm_center_y,
                    'center_x': center_x,
                    'center_y': center_y,
                    'xmin': center_x - width/2,
                    'xmax': center_x + width/2,
                    'ymin': center_y - height/2,
                    'ymax': center_y + height/2,
                    'angle': angle,
                    'area': width * height
                }
                chevron_data.append(data_dict)

        # Look through all shm chevron objects and pick 4 with highest confidence and sort chevron objects by x coordinate
        chevron_data.sort(key=lambda x: x['area'], reverse=True)
        
        # Find the center of the 4 chevron objects
        chevron_objects_centers = [(chevron_data[i]['center_x'], chevron_data[i]['center_y']) for i in range(len(chevron_data))]
        true_chevron = [True for i in range(len(chevron_data))]

        
        chevron_cnt = len(chevron_data)

        if chevron_cnt == 0:
            self.consistency.clear()
        elif chevron_cnt < 4:
            # make sure we have at least 4 chevrons
            for _ in range(4 - chevron_cnt):
                chevron_objects_centers.append((0, 0))
                true_chevron.append(False)
        else:
            # TODO: is this really necessary? For exmaple, the fifth chevron (while less confident) could be a real cheveron and the fourth one could be a false positive
            # make sure we only have 4 chevrons
            chevron_objects_centers = chevron_objects_centers[:4]
            true_chevron = true_chevron[:4]
        
        # print([x['area'] for x in chevron_data])

        chevron_cnt = len(chevron_data)
        
        self.consistency.update(chevron_objects_centers, true_chevron)
        consistent_centers = self.consistency.value()
        valid_centers = self.consistency.valid()
        
        # Remap chevron_objects and draw a circle around the center of the chevron objects
        for i in range(len(consistent_centers)):
            shm_name = f"chevron_{i+1}"
            if valid_centers[i]:
                # Draw a circle around the center of the chevron objects
                draw_circle(img, (int(consistent_centers[i][0]), int(consistent_centers[i][1])), 20, colors[i], 20)

                # Find the chevron object that matches with the consistent center
                for j in range(len(chevron_data)):
                    if chevron_data[j]['xmin'] <= consistent_centers[i][0] and chevron_data[j]['xmax'] >= consistent_centers[i][0] and chevron_data[j]['ymin'] <= consistent_centers[i][1] and chevron_data[j]['ymax'] >= consistent_centers[i][1]:
                        shm_name = f"chevron_{j+1}"

                        obj = chevron_data[j]
                        norm_center_x = obj['norm_center_x']
                        norm_center_y = obj['norm_center_y']
                        center_x = obj['center_x']
                        center_y = obj['center_y']
                        angle = obj['angle']
                        area = obj['area']
                        xmin = obj['xmin']
                        xmax = obj['xmax']
                        ymin = obj['ymin']
                        ymax = obj['ymax']

                        width = xmax - xmin
                        height = ymax - ymin
                        
                        draw_rot_rect(img, center_x, center_y, width, height, angle, colors[i], 4)
                        draw_text(img, str(i+1), (int(center_x), int(center_y)), color=colors[i], scale=5, thickness=5)


                        # text_dist=200
                        # draw_text(img, str(round(contour_area(cnt)/(width*height),2)), (int(center_x+text_dist), int(center_y)), 2, thickness=5)
                        # draw_text(img, str(round(angle,2)), (int(center_x-text_dist), int(center_y)), 2, thickness=5)

                        try:
                            getattr(shm, f"yolo_{shm_name}").angle.set(angle)
                            getattr(shm, f"yolo_{shm_name}").area.set(area)
                            getattr(shm, f"yolo_{shm_name}").center_x.set(norm_center_x)
                            getattr(shm, f"yolo_{shm_name}").center_y.set(norm_center_y)
                            getattr(shm, f"yolo_{shm_name}").visible.set(1)
                            getattr(shm, f"yolo_{shm_name}").xmin.set(xmin)
                            getattr(shm, f"yolo_{shm_name}").xmax.set(xmax)
                            getattr(shm, f"yolo_{shm_name}").ymin.set(ymin)
                            getattr(shm, f"yolo_{shm_name}").ymax.set(ymax)
                            getattr(shm, f"yolo_{shm_name}").visible.set(1)

                        except AttributeError as e:
                            print(e)
                        break
            else:
                getattr(shm, f"yolo_{shm_name}").visible.set(0)

        self.post("final", img)

    

if __name__ == '__main__':
    OctagonChevronsVision("downward", options=module_options)()
