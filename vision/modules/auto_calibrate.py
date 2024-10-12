#!/usr/bin/env python3
import shm
import numpy as np
import cv2 

from conf.vehicle import cameras, is_mainsub

from vision.core.base import ModuleBase
from vision.core.options import IntOption, BoolOption, DoubleOption
from vision.utils.draw import draw_rect, draw_text

from vision.utils.color import bgr_to_lab, lab_to_bgr

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

    if width == 0:
        width = 640
    if height == 0:
        height = 512
        
    return [
        BoolOption(f'debug', False),
        BoolOption(f'enable', True),
        BoolOption(f'enable_bright', True),
        BoolOption(f'enable_color', True),
        BoolOption(f'focus', False),
        IntOption(f'focus_x', width // 2, 0, width),
        IntOption(f'focus_y', height // 2, 0, height),
        IntOption(f'focus_width', 10, 0, min(width, height)),
        IntOption(f'target_brightness', brightness, 0, 255),
        IntOption(f'bright_acceptable_error', 20, 0, 255),
        IntOption(f'color_acceptable_error', 20, 0, 255),
        DoubleOption(f'adjustment_smoothing', 2.5, 0.1, 10),
        IntOption(f'color_x_pos', width // 2, 0, width),
        IntOption(f'color_y_pos', height - 64, 0, height),
        IntOption(f'color_width', width // 4, 0, width // 2),
        IntOption(f'color_height', 32, 0, height // 2),
    ]
    
class AutoCalibrate(ModuleBase):
    
    def __init__(self, direction):
        super().__init__(direction, get_module_options(direction))
        self.direction = direction
        self.directions = [direction]
        self.module_name = f"AutoCalibrate_{direction}"
        
        self.set_shm(shm.camera_calibration, 'exposure', 0)
        self.set_shm(shm.camera_calibration, 'red_gain', 0)
        self.set_shm(shm.camera_calibration, 'green_gain', 0)
        self.set_shm(shm.camera_calibration, 'blue_gain', 0)
    
        self.reset_debug_text()

    def get_shm(self, group, name):
        return getattr(group, f"{self.direction}_{name}").get()
    
    def set_shm(self, group, name, value):
        return getattr(group, f"{self.direction}_{name}").set(value)
    
    def update_value(self, img, shm_var, multiplier, min_val, max_val):
        current_val = self.get_shm(shm.camera_calibration, shm_var)
        
        target = current_val * multiplier
        target = max(min_val, target)
        target = min(max_val, target)
        
        r = np.exp(-0.1 / self.options['adjustment_smoothing'])
        target += r * (current_val - target)
        
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
            self.debug_text_pos = (self.debug_text_pos[0], self.debug_text_pos[1] + 32)
    
    def process(self, img):
        self.reset_debug_text()
        
        enabled = self.options['enable']
        
        (b, g, r) = cv2.split(img)
        _, lab_img = bgr_to_lab(img)
        (lab_l, lab_a, lab_b) = lab_img
        
        bgr_lab_l, (_, _, _) = lab_to_bgr(cv2.merge([lab_l, np.zeros_like(lab_l) + 128, np.zeros_like(lab_l) + 128]))
        bgr_lab_ab, (_, _, _) = lab_to_bgr(cv2.merge([np.zeros_like(lab_a) + 128, lab_a, lab_b]))
        
        bgr_r = cv2.merge([np.zeros_like(r), np.zeros_like(r), r])
        bgr_g = cv2.merge([np.zeros_like(g), g, np.zeros_like(g)])
        bgr_b = cv2.merge([b, np.zeros_like(b), np.zeros_like(b)])
        
        self.width = self.get_shm(shm.camera, 'width')
        self.height = self.get_shm(shm.camera, 'height')
        
        focus = self.options['focus']
        
        if focus:
            focus_x = self.options['focus_x']
            focus_y = self.options['focus_y']
            focus_width = self.options['focus_width']
            
            start_x = max(0, focus_x - focus_width)
            start_y = max(0, focus_y - focus_width)
            
            end_x = min(self.width, focus_x + focus_width)
            end_y = min(self.height, focus_y + focus_width)
            
            draw_rect(img, (start_x, start_y), (end_x, end_y), color=(255, 255, 255), thickness=5)
            draw_rect(lab_l, (start_x, start_y), (end_x, end_y), color=(255, 255, 255), thickness=5)
        
        if enabled and self.options['enable_bright']:
            self.draw_debug_text(img, "---= EXPOSURE =---")
            
            if focus:
                brightness_average = np.average(lab_l[start_x:end_x, start_y:end_y])
            else:
                brightness_average = np.average(lab_l)
                
            self.draw_debug_text(img, f"  1) brightness average: {brightness_average:.2f}")
                
            exposure = self.get_shm(shm.camera_calibration, 'exposure')
            target_bright = self.options['target_brightness']
            
            self.draw_debug_text(img, f"  2) exposure: {exposure:.2f}")
            
            if abs(brightness_average - target_bright) > self.options['bright_acceptable_error']:
                self.update_value(img, 'exposure', target_bright / brightness_average, 1, 100)
            
            self.draw_debug_text(img, f"")
            
        elif enabled:
            self.set_shm(shm.camera_calibration, 'exposure', 0)
                    
        if enabled and self.options['enable_color']:
            color_x_pos = self.options['color_x_pos']
            color_y_pos = self.options['color_y_pos']
            color_width = self.options['color_width']
            color_height = self.options['color_height']

            rect_top_left = (color_x_pos - color_width, color_y_pos - color_height)
            rect_bottom_right = (color_x_pos + color_width, color_y_pos + color_height)
            draw_rect(img, rect_top_left, rect_bottom_right, color=(255, 0, 0), thickness=5)
            draw_rect(bgr_lab_ab, rect_top_left, rect_bottom_right, color=(255, 0, 0), thickness=5)
            
            self.draw_debug_text(img, "----= COLOR =----")
            red_gain = self.get_shm(shm.camera_calibration, 'red_gain')
            green_gain = self.get_shm(shm.camera_calibration, 'green_gain')
            blue_gain = self.get_shm(shm.camera_calibration, 'blue_gain')
            
            red_mean = np.mean(r[color_y_pos - color_height:color_y_pos + color_height, color_x_pos - color_width:color_x_pos + color_width])
            green_mean = np.mean(g[color_y_pos - color_height:color_y_pos + color_height, color_x_pos - color_width:color_x_pos + color_width])
            blue_mean = np.mean(b[color_y_pos - color_height:color_y_pos + color_height, color_x_pos - color_width:color_x_pos + color_width])
            
            if np.min([red_mean, green_mean, blue_mean]) <= 4:
                self.draw_debug_text(img, "  1) color box too dark to calibrate!")
            else:
                scaling_factor = 256 / np.sum([red_mean, green_mean, blue_mean])
                red_mean *= scaling_factor
                green_mean *= scaling_factor
                blue_mean *= scaling_factor
                
                self.draw_debug_text(img, f"  1a) red mean: {red_mean:.2f}")
                self.draw_debug_text(img, f"  1b) red gain: {red_gain:.2f}")
                self.draw_debug_text(img, f"  2a) green mean: {green_mean:.2f}")
                self.draw_debug_text(img, f"  2b) green gain: {green_gain:.2f}")
                self.draw_debug_text(img, f"  3a) blue mean: {blue_mean:.2f}")
                self.draw_debug_text(img, f"  3b) blue gain: {blue_gain:.2f}")
                
                acceptable_error = self.options['color_acceptable_error']
                
                average_gain = np.mean([red_gain, green_gain, blue_gain])
                average_mean = np.mean([red_mean, green_mean, blue_mean])
                max_average_error = np.max(np.abs([red_mean, green_mean, blue_mean] - average_mean))
                
                average_color_gain = 33
                global_adjustment = average_color_gain / average_gain
                
                if max_average_error > acceptable_error:
                    self.update_value(img, 'red_gain', global_adjustment * (average_mean / red_mean), 1, 100)
                    self.update_value(img, 'green_gain', global_adjustment * (average_mean / green_mean), 1, 100)
                    self.update_value(img, 'blue_gain', global_adjustment * (average_mean / blue_mean), 1, 100)
                else:
                    self.update_value(img, 'red_gain', global_adjustment, 1, 100)
                    self.update_value(img, 'green_gain', global_adjustment, 1, 100)
                    self.update_value(img, 'blue_gain', global_adjustment, 1, 100)
                    
                self.draw_debug_text(img, f"")
                
        elif enabled:
            self.set_shm(shm.camera_calibration, 'red_gain', 0)
            self.set_shm(shm.camera_calibration, 'green_gain', 0)
            self.set_shm(shm.camera_calibration, 'blue_gain', 0)
        
        self.post('Final Image', img)
        
        self.post('LAB Luma Channel', bgr_lab_l)
        self.post('LAB Chroma Channel', bgr_lab_ab)
        
        self.post('RGB Red Channel', bgr_r)
        self.post('RGB Green Channel', bgr_g)
        self.post('RGB Blue Channel', bgr_b)
        
import sys
if __name__ == '__main__':
    direction = sys.argv[1]
    if direction != "default":
        AutoCalibrate(direction)()