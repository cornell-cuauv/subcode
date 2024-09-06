#!/usr/bin/env python3


from ultralytics import YOLO # For some reason, ultralytics needs to be imported before or breaks on sub

import math
from mission.framework.ssc256_consistency import ConsistentTargeting
import shm
import cv2
import numpy as np
from vision import options
from vision.framework.feature import min_enclosing_rect, outer_contours
from vision.modules.base import ModuleBase
from vision.framework.draw import draw_rect, draw_text, draw_circle, draw_arrow
from vision.framework.color import thresh_color_distance, bgr_to_lab

module_options = [
    options.IntOption('heuristic_threshold', 75, 0, 100),
    options.BoolOption("to_rgb", False),
    options.IntOption("text_scale", 5, 1, 20),
    options.IntOption("text_thiccc_ness", 5, 1, 20),
    options.BoolOption("off", False),
    options.BoolOption("clear_consistency", False),
    options.BoolOption("invert_thresh", False),
    options.IntOption('a', 146, 0, 255),
    options.IntOption('b', 157, 0, 255),
    options.IntOption('c', 150, 0, 255),
    options.IntOption('dist', 25, 0, 50),
]

# Claw Pixel Position on Downcam
# X: 325, Y:125

colors = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255), (170, 110, 40), (255, 250, 200), (128, 0, 0), (170, 255, 195), (128, 128, 0), (255, 215, 180), (0, 0, 128), (128, 128, 128), (255, 255, 255), (0, 0, 0)]

# Mapping is just results.name from model
mapping = {0: 'abin1', 1: 'abin2', 2: 'belt', 3: 'center', 4: 'chevron', 5: 'claw', 6: 'cover', 7: 'curve', 8: 'dipper', 9: 'dragon', 10: 'ebin1', 11: 'faucet', 12: 'gcenter', 13: 'gleft', 14: 'gright', 15: 'handle', 16: 'lightning', 17: 'nozzle', 18: 'octagon', 19: 'shovel', 20: 'slingshot', 21: 'triangle', 22: 'wishbone'}

class Yolo(ModuleBase):
    print("Loading model...")
    model = YOLO('vision/yolo/auv_models/everythin640v3.pt')
    consistency = ConsistentTargeting(20, 'pos', num_detections=4)

    def process(self, img):
        if self.options["off"]:
            self.consistency.clear()
            return

        if self.options["clear_consistency"]:
            self.consistency.clear()
            self.options["clear_consistency"] = False

        threshed = self.color_filter(img)

        # ######################################
        # ---------- SHM Data Setup ---------- #
        # ######################################
        chevron_cnt = 0
        mapped_shm = {} # list of shm objects that were detected
        for shm_name in mapping.values():
            mapped_shm[shm_name] = {
                'angle': 0,
                'area': 0,
                'center_x': 0,
                'center_y': 0,
                'confidence': 0,
                'visible': 0,
                'xmax': 0,
                'xmin': 0,
                'ymax': 0,
                'ymin': 0,
                'int_name': 0,
            }

        # Convert to RGB if necessary
        if self.options["to_rgb"]:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # ######################################
        # ---------- Model Infer ------------- #
        # ######################################
        results = self.model(img, verbose=False) # stream=True to avoid copying img to gpu
        
        # ######################################
        # ---------- Data Read and Update ---- #
        # ######################################
        for result in results:
            result = result.cpu()
            boxes = result.boxes.xyxy.numpy()
            class_name = result.boxes.cls
            conf = result.boxes.conf
                    
            # Write to shm and Visualize
            for idx in range(0, len(boxes)):
                angle = 0
                x1, y1, x2, y2 = boxes[idx]
                ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
                x, y = (int((ix1 + ix2) / 2), int((iy1 + iy2) / 2))
                area = (x2 - x1) * (y2 - y1)
                heuristic = conf[idx].item()
                int_name = int(class_name[idx].item())
                shm_name = mapping[int_name]

                if heuristic < self.options["heuristic_threshold"] / 100.0:
                    continue

                if "chevron" in shm_name:
                    shm_name = f"{shm_name}_{str(chevron_cnt+1)}"

                    # ######################################
                    # ---------- Angle Calculate 1 ------- #
                    # ######################################
                    # Calculate Angle by figuring out direction of long side and scaling it 
                    scaled_width = (ix2 - ix1) / area
                    scaled_height = (iy2 - iy1) / area

                    ratio = scaled_width / scaled_height

                    # print(f"w: {scaled_width}, h: {scaled_height}, ratio: {ratio}")
                    # ratio of 1.4 means angle of 90
                    # ratio of 0.8 means angle of 0
                    angle = (ratio - 0.8) * 90 / 0.6

                    # ######################################
                    # ---------- Angle Calculate 2 ------- #
                    # ######################################
                    local_threshed = threshed[iy1:iy2, ix1:ix2]

                    # self.post(f"chevron{chevron_cnt}", local_threshed)

                    clist = outer_contours(local_threshed)
                    # take the largest contour
                    if len(clist) > 0:
                        max_clist = max(clist, key=cv2.contourArea)
                        # get the angle of the contour
                        (center_x, center_y), (width, height), angle = min_enclosing_rect(max_clist)
                        # print(height > width)
                        if width > height:
                            angle += 90

                        angle = angle % 180

                        if angle > 90:
                            angle = 180 - angle

                    mapped_shm[shm_name] = {
                        'angle': angle,
                        'area': area,
                        'center_x': x,
                        'center_y': y,
                        'confidence': heuristic,
                        'visible': 1,
                        'xmax': ix2,
                        'xmin': ix1,
                        'ymax': iy2,
                        'ymin': iy1,
                        'int_name': int_name,
                    }
                    chevron_cnt += 1
                else:
                    mapped_shm[shm_name] = {
                        'angle': angle,
                        'area': (x2 - x1) * (y2 - y1),
                        'center_x': x,
                        'center_y': y,
                        'confidence': heuristic,
                        'visible': 1,
                        'xmax': ix2,
                        'xmin': ix1,
                        'ymax': iy2,
                        'ymin': iy1,
                        'int_name': int_name,
                    }        

        # Look through all shm chevron objects and pick 4 with highest confidence and sort chevron objects by x coordinate
        chevron_objects = [mapped_shm[f"chevron_{i+1}"] for i in range(len(mapped_shm)) if f"chevron_{i+1}" in mapped_shm]
        chevron_objects.sort(key=lambda x: x['confidence'], reverse=True)
        # chevron_objects.sort(key=lambda x: x['center_x'])

        # Find the center of the 4 chevron objects
        chevron_objects_centers = [(chevron_objects[i]['center_x'], chevron_objects[i]['center_y']) for i in range(len(chevron_objects))]
        true_chevron = [True for i in range(len(chevron_objects))]

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
        
        self.consistency.update(chevron_objects_centers, true_chevron)
        consistent_centers = self.consistency.value()
        valid_centers = self.consistency.valid()

        # Remap chevron_objects and draw a circle around the center of the chevron objects
        for i in range(len(consistent_centers)):
            if valid_centers[i]:
                # Draw a circle around the center of the chevron objects
                draw_circle(img, (int(consistent_centers[i][0]), int(consistent_centers[i][1])), 10, colors[i], 10)

                # Find the chevron object that matches with the consistent center
                for j in range(len(chevron_objects)):
                    if chevron_objects[j]['xmin'] <= consistent_centers[i][0] and chevron_objects[j]['xmax'] >= consistent_centers[i][0] and chevron_objects[j]['ymin'] <= consistent_centers[i][1] and chevron_objects[j]['ymax'] >= consistent_centers[i][1]:
                        mapped_shm[f"chevron_{i+1}"] = chevron_objects[j]

            else:
                mapped_shm[f"chevron_{i+1}"] = {
                    'angle': 0,
                    'area': 0,
                    'center_x': 0,
                    'center_y': 0,
                    'confidence': 0,
                    'visible': 0,
                    'xmax': 0,
                    'xmin': 0,
                    'ymax': 0,
                    'ymin': 0,
                    'int_name': 0,
                }                
        
        for shm_name in mapped_shm.keys():
            angle = mapped_shm[shm_name]['angle']
            area = mapped_shm[shm_name]['area']
            center_x = mapped_shm[shm_name]['center_x']
            center_y = mapped_shm[shm_name]['center_y']
            norm_x, norm_y = self.normalized((center_x, center_y))
            confidence = mapped_shm[shm_name]['confidence']
            visible = mapped_shm[shm_name]['visible']
            xmax = mapped_shm[shm_name]['xmax']
            xmin = mapped_shm[shm_name]['xmin']
            ymax = mapped_shm[shm_name]['ymax']
            ymin = mapped_shm[shm_name]['ymin']
            int_name = mapped_shm[shm_name]['int_name']

            width = xmax - xmin
            height = ymax - ymin

            draw_rect(img, (xmin, ymin), (xmax, ymax), thickness=self.options["text_thiccc_ness"], color=colors[int_name % len(colors)])
            text_to_display = shm_name[0:3] + shm_name[-1] + " " + str(int(confidence*100))
            draw_text(img, text_to_display, (int(xmin), int(center_y)), color=colors[int_name % len(colors)], scale=self.options["text_scale"], thickness=self.options["text_thiccc_ness"])

            if shm_name == "chevron":
                continue
            elif "chevron" in shm_name:
                draw_arrow(img, (int(center_x), int(center_y)), (int(center_x + 2 * width * math.cos(math.radians(angle))), int(center_y + 2 * height * math.sin(math.radians(angle)))), (0, 0, 255), 10)
                

            try:
                getattr(shm, f"yolo_{shm_name}").angle.set(angle)
                getattr(shm, f"yolo_{shm_name}").area.set(area)
                getattr(shm, f"yolo_{shm_name}").center_x.set(norm_x)
                getattr(shm, f"yolo_{shm_name}").center_y.set(norm_y)
                getattr(shm, f"yolo_{shm_name}").visible.set(visible)
                getattr(shm, f"yolo_{shm_name}").xmax.set(xmax)
                getattr(shm, f"yolo_{shm_name}").xmin.set(xmin)
                getattr(shm, f"yolo_{shm_name}").ymax.set(ymax)
                getattr(shm, f"yolo_{shm_name}").ymin.set(ymin)
                getattr(shm, f"yolo_{shm_name}").confidence.set(confidence)
            except AttributeError as e:
                print(e)
            

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

        if self.options["invert_thresh"]:
            threshed = cv2.bitwise_not(threshed)

        self.post("threshed", threshed)

        return threshed

if __name__ == '__main__':
    Yolo(["downward"], module_options)()