#!/usr/bin/env python3
from ultralytics import YOLO # For some reason, ultralytics needs to be imported before or breaks on sub

import math
import shm
import cv2
import numpy as np
from vision import options
from vision.framework.feature import min_enclosing_rect, outer_contours
from vision.modules.base import ModuleBase
from vision.framework.draw import draw_rect, draw_text, draw_circle, draw_arrow
from vision.framework.color import thresh_color_distance, bgr_to_lab

module_options = [
    options.IntOption('heuristic_threshold', 10, 0, 100),
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


colors = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255), (170, 110, 40), (255, 250, 200), (128, 0, 0), (170, 255, 195), (128, 128, 0), (255, 215, 180), (0, 0, 128), (128, 128, 128), (255, 255, 255), (0, 0, 0)]


class Yolo(ModuleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Loading YOLO")
        self.model = YOLO('/home/software/cuauv/workspaces/worktrees/master/vision/modules/yolo/best.pt')
        print("Loaded YOLO")


    def process(self, img):
        self.post("orig", img)
        
        # ######################################
        # ---------- SHM Data Setup ---------- #
        # ######################################
        chevron_cnt = 0
        mapping= {0:'torpedos_board'}
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
        
        # ######################################
        # ---------- Model Infer ------------- #
        # ######################################
        results = self.model(img, verbose=False) # stream=True to avoid copying img to gpu
        print(results)
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



if __name__ == '__main__':
    Yolo(["forward"], module_options)()
