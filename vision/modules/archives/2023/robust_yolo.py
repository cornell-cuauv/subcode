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
from vision.framework.draw import draw_rect, draw_text, draw_circle, draw_arrow, draw_rot_rect
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

colors = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255), (170, 110, 40), (255, 250, 200), (128, 0, 0), (170, 255, 195), (128, 128, 0), (255, 215, 180), (0, 0, 128), (128, 128, 128), (255, 255, 255), (0, 0, 0)]

class RobustYolo(ModuleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Loading Model...")
        self.model = YOLO('vision/yolo/auv_models/everything640v4v2.pt')
        print("Model Loaded")
        
        self.chev_consistency = ConsistentTargeting(20, 'pos', num_detections=4)
        self.bin_consistency = ConsistentTargeting(20, 'pos', num_detections=2)

    def color_thresh(self, img, color, dist):
        """
        Thresholds the image based on the color of the target

        :param img: The image to threshold
        :param color: The color to threshold for
        :param dist: The distance from the color to threshold for
    
        :return: The thresholded image
        """
        lab, lab_split = bgr_to_lab(img)

        # thresh_color_distance
        threshed, _ = thresh_color_distance(lab_split, color, dist, ignore_channels=[0])

        if self.options["invert_thresh"]:
            threshed = cv2.bitwise_not(threshed)

        return threshed

    def process(self, img):
        # Initial Options
        if self.options["off"]:
            self.consistency.clear()
            return

        if self.options["clear_consistency"]:
            self.chev_consistency.clear()
            self.options["clear_consistency"] = False

        chevron_data = []

        # ######################################
        # ------- Model Infer & Thresh ------- #
        # ######################################
        threshed = self.color_thresh(img, (0, self.options['a'], self.options['b']), self.options['dist'])
        threshed_img = cv2.cvtColor(threshed, cv2.COLOR_GRAY2BGR)
        # results = self.model(img, verbose=False) # stream=True to avoid copying img to gpu
        results = self.model.track(img, verbose=False, persist=True) # can also be model.track
        final_img = results[0].plot()

        result = results[0]
        
        # TODO: Process Yolo Model
        result = result.cpu()
        boxes = result.boxes.xyxy.numpy()
        names = result.names
        names_list = list(names.values())
        # hard coding the 4 chevrons
        try:
            names_list.remove("chevron")
            names_list.append("chevron_1")
            names_list.append("chevron_2")
            names_list.append("chevron_3")
            names_list.append("chevron_4")
        except:
            print(f"No chevrons found in names_list: {names_list}")

        class_name = result.boxes.cls
        conf = result.boxes.conf

        for idx, box in enumerate(boxes):
            angle = 0
            xmin, ymin, xmax, ymax = boxes[idx]
            ixmin, iymin, ixmax, iymax = int(xmin), int(ymin), int(xmax), int(ymax)
            centerx, centery = (int((xmin + xmax) / 2), int((ymin + ymax) / 2))
            normx, normy = self.normalized((centerx, centery))
            area = (xmax - xmin) * (ymax - ymin)
            confidence = conf[idx].item()
            int_name = int(class_name[idx].item())
            shm_name = names[int_name]

            if confidence >= self.options["heuristic_threshold"] / 100.0:
                if shm_name in names_list:
                    names_list.remove(shm_name)
                if "chevron" in shm_name:
                    # ############################j##########
                    # ---------- Angle Calculate 1 ------- #
                    # ######################################
                    # Calculate Angle by figuring out direction of long side and scaling it 
                    scaled_width = (xmax - xmin) / area
                    scaled_height = (ymax - ymin) / area

                    ratio = scaled_width / scaled_height

                    # print(f"w: {scaled_width}, h: {scaled_height}, ratio: {ratio}")
                    # ratio of 1.4 means angle of 90
                    # ratio of 0.8 means angle of 0
                    angle = (ratio - 0.8) * 90 / 0.6

                    # ######################################
                    # ---------- Angle Calculate 2 ------- #
                    # ######################################
                    local_threshed = threshed[iymin:iymax, ixmin:ixmax]

                    clist = outer_contours(local_threshed)
                    # take the largest contour
                    if len(clist) > 0:
                        max_clist = max(clist, key=cv2.contourArea)
                        # get the angle of the contour
                        (_, _), (width, height), angle = min_enclosing_rect(max_clist)
                        draw_rot_rect(threshed_img, centerx, centery, width, height, angle, colors[idx], 4)

                        # Angle should always be from long side of chevron
                        if width > height:
                            angle += 90

                        if angle > 90:
                            angle -= 180


                    chevron_data.append({
                        'angle': angle,
                        'area': area,
                        'center_x': centerx,
                        'center_y': centery,
                        'normx': normx,
                        'normy': normy,
                        'confidence': confidence,
                        'visible': 1,
                        'xmax': xmax,
                        'xmin': xmin,
                        'ymax': ymax,
                        'ymin': ymin,
                        'int_name': int_name,
                    })
                elif "bin" in shm_name:
                    pass
                else:
                    try:
                        getattr(shm, f"yolo_{shm_name}").angle.set(angle)
                        getattr(shm, f"yolo_{shm_name}").area.set(area)
                        getattr(shm, f"yolo_{shm_name}").center_x.set(normx)
                        getattr(shm, f"yolo_{shm_name}").center_y.set(normy)
                        getattr(shm, f"yolo_{shm_name}").visible.set(1)
                        getattr(shm, f"yolo_{shm_name}").xmax.set(xmax)
                        getattr(shm, f"yolo_{shm_name}").xmin.set(xmin)
                        getattr(shm, f"yolo_{shm_name}").ymax.set(ymax)
                        getattr(shm, f"yolo_{shm_name}").ymin.set(ymin)
                        getattr(shm, f"yolo_{shm_name}").confidence.set(confidence)
                    except AttributeError as e:
                        print(e)

        # TODO: Tracking and reordering chevrons and bins and putting into shm
        chevron_data.sort(key=lambda x: x['confidence'], reverse=True)
        chevron_data_centers=[(chevron_data[i]['center_x'], chevron_data[i]['center_y']) for i in range(len(chevron_data))]
        true_chevron = [True for i in range(len(chevron_data))]

        if len(chevron_data) == 0:
            self.chev_consistency.clear()
        elif len(chevron_data) < 4:
            # make sure we have at least 4 chevrons
            for _ in range(4 - len(chevron_data)):
                chevron_data_centers.append((0, 0))
                true_chevron.append(False)
                chevron_data.append(None)
        else:
            chevron_data_centers = chevron_data_centers[:4]
            true_chevron = true_chevron[:4]
            chevron_data = chevron_data[:4]

        # print("Inputs:", chevron_data_centers, true_chevron)
        self.chev_consistency.update(chevron_data_centers, true_chevron, metadata_lst=chevron_data)
        consistent_centers = self.chev_consistency.value()
        valid_centers = self.chev_consistency.valid()
        chev_metadata = self.chev_consistency.get_metadata()
        # print("Outputs:", consistent_centers, valid_centers)
        print()

        for i in range(len(consistent_centers)):
            if valid_centers[i]:
                if shm_name in names_list:
                    names_list.remove(shm_name)
                # Draw a circle around the center of the chevron objects
                angle = chev_metadata[i]['angle']
                area = chev_metadata[i]['area']
                center_x, center_y = chev_metadata[i]['center_x'], chev_metadata[i]['center_y']
                confidence = chev_metadata[i]['confidence']
                xmin, ymin, xmax, ymax = chev_metadata[i]['xmin'], chev_metadata[i]['ymin'], chev_metadata[i]['xmax'], chev_metadata[i]['ymax']
                width = xmax - xmin
                height = ymax - ymin

                draw_circle(threshed_img, (int(consistent_centers[i][0]), int(consistent_centers[i][1])), 10, colors[i], 30)
                draw_arrow(threshed_img, (int(center_x), int(center_y)), (int(center_x + 2 * width * math.cos(math.radians(angle))), int(center_y + 2 * height * math.sin(math.radians(angle)))), colors[i], 10)
                
                # Add to SHM
                shm_name = f"chevron_{i+1}"
                getattr(shm, f"yolo_{shm_name}").angle.set(angle)
                getattr(shm, f"yolo_{shm_name}").area.set(area)
                getattr(shm, f"yolo_{shm_name}").center_x.set(normx)
                getattr(shm, f"yolo_{shm_name}").center_y.set(normy)
                getattr(shm, f"yolo_{shm_name}").visible.set(1)
                getattr(shm, f"yolo_{shm_name}").xmax.set(xmax)
                getattr(shm, f"yolo_{shm_name}").xmin.set(xmin)
                getattr(shm, f"yolo_{shm_name}").ymax.set(ymax)
                getattr(shm, f"yolo_{shm_name}").ymin.set(ymin)
                getattr(shm, f"yolo_{shm_name}").confidence.set(confidence)

        # TODO: Reset SHM for all objects that were not detected
        for shm_name in names_list:
            try:
                getattr(shm, f"yolo_{shm_name}").visible.set(0)
            except:
                print(f"Could not set {shm_name} to invisible")

        self.post("final", final_img)
        self.post("thresh", threshed_img)

if __name__ == '__main__':
    RobustYolo(["downward"], module_options)()
    
