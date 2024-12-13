#!/usr/bin/env python3
import shm
import numpy as np
import cv2 

from conf.vehicle import cameras, is_mainsub

import shm.camera_calibration
from vision.core.base import ModuleBase
from vision.core.options import IntOption, BoolOption, DoubleOption
from vision.utils.draw import draw_rect, draw_text

from vision.utils.color import bgr_to_lab, lab_to_bgr, bgr_to_hsv, bgr_to_gray

def get_module_options(direction):
    brightness = {
        (True, True): 152,
        (True, False): 172,
        (False, True): 180,
        (False, False): 150
    }[(is_mainsub, direction == 'forward')]

    try:     
        width = getattr(cameras, direction).width
        height = getattr(cameras, direction).height
    except AttributeError:
        width = 640
        height = 512

    return [
            BoolOption(f'debug', False),
            BoolOption(f'enable', True),
            DoubleOption(f'adjustment_smoothing', 2.5, 0.1, 10),
            IntOption('target_zed_contrast'     ,   40, 0, 127),
            IntOption('target_zed_hue'          ,   20, 0, 180),
            IntOption('target_zed_saturation'   ,   150, 0, 8),
            IntOption(f'target_brightness', brightness, 0, 11),
            IntOption(f'bright_acceptable_error', 20, 0, 255),
            IntOption(f'hue_acceptable_error', 20, 0, 180),
            IntOption(f'contrast_acceptable_error', 15, 0, 127),
    ]
    
class AutoCalibrateZed(ModuleBase):
    def __init__(self, direction):
        super().__init__(direction, get_module_options(direction))
        self.direction = direction
        self.directions = [direction]
        self.module_name = f"AutoCalibrateZed_{direction}"
        self.reset_debug_text()
    
    def get_shm(self,group,name):
        return getattr(group, f"{name}").get()
    
    def set_shm(self, group, name, value):
        return getattr(group, f"{name}").set(value)
    
    def update_value(self, img, shm_var, multiplier, min_val, max_val):
        current_val = self.get_shm(shm.camera_calibration, shm_var)
        target = current_val * multiplier
        target = max(min_val, target)
        target = min(max_val, target)
        
        r = np.exp(-0.1 / self.options['adjustment_smoothing'])
        target += r * (current_val - target)
        target = round(target)

        self.set_shm(shm.camera_calibration, shm_var, target)
    
    def update_hue(self,img,shm_var,target_hue,current_hue):
        # 0: No hue shift (natural colors).
        # 1-2: Shift toward red tones.
        # 3-4: Shift toward orange/yellow tones.
        # 5-6: Shift toward green tones.
        # 7-8: Shift toward cyan/blue tones.
        # 9-10: Shift toward violet/purple tones.
        # 11: Shift through the color wheel back to near the original natural color (similar to 0).

        current_val = self.get_shm(shm.camera_calibration,shm_var)
        if current_val == 11:
            current_val = 0

        hue_shift = round(target_hue-current_hue) 
        print('hue_shift',hue_shift)
        target = round((current_val + hue_shift/18) % 11)
        print('set target',target)
        self.set_shm(shm.camera_calibration, shm_var, target)
    

    def reset_debug_text(self):
        self.debug_text_pos = (25, 40)

    def draw_debug_text(self, img, text):
        if self.options['debug']:
            average_color = np.mean(img[self.debug_text_pos[1] + 16, :, :])
            if average_color < 127:
                text_color = (255, 255, 255)  # white
                text_outline = (0, 0, 0)  # black
            else:
                text_color = (0, 0, 0)  # black
                text_outline = (255, 255, 255)  # white
            
            draw_text(img, text, self.debug_text_pos, 0.8, color=text_outline, thickness=8)
            draw_text(img, text, self.debug_text_pos, 0.8, color=text_color, thickness=2)


    def process(self, img):
        self.reset_debug_text()
        enabled = self.options['enable']

        _, lab_img = bgr_to_lab(img)
        _, hsv_img = bgr_to_hsv(img)
        (lab_l, lab_a, lab_b) = lab_img
        (hsv_h, hsv_s, hsv_v) = hsv_img
        gray_img = bgr_to_gray(img)

        if enabled:
            # currently not autotuning Gamma and Sharpness
        
            # Exposure
            # brightness_average = np.average(lab_l)
            
            # target_bright = self.options['target_brightness']
            # print('curr',brightness_average)
            # print('target',target_bright)
            # print('acceptable error', self.options['bright_acceptable_error'])
            # self.draw_debug_text(img, f"  1) brightness average: {brightness_average:.2f}")
            # if abs(brightness_average - target_bright) > self.options['bright_acceptable_error']:
            #     # print('calling update')
            #     self.update_value(img, 'zed_exposure', target_bright / brightness_average, 0, 100)
            
            # # Gain
            # brightness_average = np.average(lab_l)
            # target_bright = self.options['target_brightness']
            # self.draw_debug_text(img, f"  1) brightness average: {brightness_average:.2f}")
            # if abs(brightness_average - target_bright) > self.options['bright_acceptable_error']:
            #     self.update_value(img, 'zed_gain', target_bright / brightness_average, 0, 100)
            
            # # Brightness
            # brightness_average = np.average(lab_l)
            # target_bright = self.options['target_brightness']
            # self.draw_debug_text(img, f"  1) brightness average: {brightness_average:.2f}")
            # if abs(brightness_average - target_bright) > self.options['bright_acceptable_error']:
            #     self.update_value(img, 'zed_brightness', target_bright / brightness_average, 0, 8)
            
            # # White Balance
            # brightness_average = np.average(lab_l)
            # target_bright = self.options['target_brightness']
            # self.draw_debug_text(img, f"  1) brightness average: {brightness_average:.2f}")
            # if abs(brightness_average - target_bright) > self.options['bright_acceptable_error']:
            #     self.update_value(img, 'zed_white_balance', target_bright / brightness_average, 2800, 6500)
            

            # Contrast
            # contrast = np.std(gray_img)
            # target_contrast = self.options['target_contrast']
            # if abs(contrast - target_contrast) > self.options['contrast_acceptable_error']:
            #     self.update_value(img, 'zed_contrast', target_contrast / contrast, 0, 8)

            # # Saturation
            # saturation_average = np.average(hsv_s)
            # target_saturation = self.options['target_saturation']
            # self.draw_debug_text(img, f"  1) saturation average: {saturation_average:.2f}")
            # if abs(contrast - target_contrast) > self.options['contrast_acceptable_error']:
            #     self.update_value(img, 'zed_saturation', target_saturation/saturation_average, 0, 8)

            # # Hue
            
            hue_average = np.average(hsv_h)
            target_hue = self.options['target_zed_hue']

            print('curr_hue',hue_average)
            print('target',target_hue)
            print('acceptable error', self.options['hue_acceptable_error'])
            self.draw_debug_text(img, f"  1) hue average: {hue_average:.2f}")
            if abs(hue_average - target_hue) > self.options['hue_acceptable_error']:
                print('updating supposedly')
                self.update_hue(img,'zed_hue',target_hue,hue_average)

import sys          
if __name__ == '__main__':
    direction = sys.argv[1]
    if direction != "default":
        AutoCalibrateZed(direction)()