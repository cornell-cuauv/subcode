#!/usr/bin/env python3
import shm
import numpy as np
import ctypes
import cv2 
import time

from conf.vehicle import cameras, is_mainsub

from vision.modules.base import ModuleBase
from vision import options
from vision.framework.draw import draw_rect, draw_text

from vision.framework.color import bgr_to_lab

directions = list(cameras.keys())
camera_vars = shm.camera.get()

module_options = [
            options.BoolOption('debug', False),
            options.BoolOption('enable', True)
]


def gen_start(direction):
    if is_mainsub:
        if direction == 'forward':
            return 152
        else:
            return 180
    else:
        if direction == 'forward':
           return 172
        else:
            return 150


def gen_opts():
    for i in range(len(directions)):
        d = directions[i]
        #width = getattr(camera_vars,d + "_width")
        #height = getattr(camera_vars,d + "_height")
        width = 1280
        height = 1024

        module_options.append(options.BoolOption(d + '_enable_bright',True))
        module_options.append(options.BoolOption(d + '_enable_color',False))
        module_options.append(options.BoolOption(d + '_focus',False))
        module_options.append(options.IntOption(d + '_focus_x',width // 2,0,width))
        module_options.append(options.IntOption(d + '_focus_y',height // 2,0,height))
        module_options.append(options.IntOption(d + '_focus_width',10,0,min(width,height)))
        module_options.append(options.IntOption(d + '_target_brightness', gen_start(d), 0, 255))
        module_options.append(options.DoubleOption(d + '_bright_delta',0.4,0,1.2))
        module_options.append(options.IntOption(d + '_bright_acceptable_error',20,0,255))
        module_options.append(options.IntOption(d + '_color_delta',2,0,20))
        module_options.append(options.IntOption(d + '_color_acceptable_error',20,0,255))
        module_options.append(options.IntOption(d + '_red_x_pos',664,0,width))
        module_options.append(options.IntOption(d + '_red_y_pos',936,0,height))
        module_options.append(options.IntOption(d + '_blue_x_pos',664,0,width))
        module_options.append(options.IntOption(d + '_blue_y_pos',936,0,height))
        module_options.append(options.IntOption(d + '_green_x_pos',664,0,width))
        module_options.append(options.IntOption(d + '_green_y_pos',936,0,height))
    return module_options


class AutoCalibrate(ModuleBase):
    def __init__(self, directions):
        super().__init__(directions,gen_opts())
    
    def process(self, *mats):
        #time.sleep(0.5)
        targets = ["red","blue","green","bright"]
        shm_name = { "red":"red_gain", "blue":"blue_gain", "green":"green_gain", "bright":"exposure" }
        min_vals = { k:0 for k in targets }
        max_vals = { k:100 for k in targets }

        # direction must be a valid camera direction string (ex "forward"), target must be one of "red", "blue", "green", or "bright"
        def update_value(direction, target, delta, debug):
            if not (target in targets):
                print("Aborting update: target " + target + " not valid")
                return False
            negative = (delta < 0)
            if debug:
                print("Calibrating " + direction + (" not " if negative else " too ") + target + (" enough." if negative else "."))
            curr_cal = getattr(shm.camera_calibration, direction + "_" + shm_name[target])
            curr_val = curr_cal.get()
            if min(100, (max(0, curr_val + delta))) != curr_val:
                curr_cal.set(min(100,(max(0, curr_val + delta))))
                return True
            else:
                return False
        debug = self.options['debug']
        for i in range(len(mats)):
            direction = directions[i]
            img = mats[i]

            (b, g, r) = cv2.split(img)
            _, lab_img = bgr_to_lab(img)
            (lab_l, lab_a, lab_b) = lab_img

            camera_height = getattr(camera_vars,direction + '_height')
            camera_width = getattr(camera_vars,direction + '_width')

            focus = self.options[direction + '_focus']
            curr_cal = shm.camera_calibration.get()
            changed = False
            if focus:
                focus_x = self.options[direction + '_focus_x']
                focus_y = self.options[direction + '_focus_y']
                focus_width = self.options[direction + '_focus_width']
                start_x = max(0,focus_x-focus_width)
                start_y = max(0,focus_y-focus_width)
                end_x = min(camera_width,focus_x+focus_width)
                end_y = min(camera_height,focus_y+focus_width)

                draw_rect(img,(start_x,start_y),(end_x,end_y),color=(255,255,255),thickness=5)
                draw_rect(lab_l,(start_x,start_y),(end_x,end_y),color=(255,255,255),thickness=5)
            draw_rect(img,(self.options[direction+'_red_x_pos']-15,self.options[direction+'_red_y_pos']-15),(self.options[direction+'_red_x_pos']+15,self.options[direction+'_red_y_pos']+15),color=(0,0,255),thickness=5)
            if(self.options[direction+'_enable_bright'] and self.options['enable']):
                if focus:
                    med_bright = np.median(lab_l[start_x:end_x,start_y:end_y])
                else:
                    med_bright = np.median(lab_l)
                if debug:
                    print("Bright median for " + direction + ": " + str(med_bright))
                bright_cal = getattr(curr_cal, direction + "_exposure")
                target_bright = self.options[direction + '_target_brightness']
                bright_delta = self.options[direction + '_bright_delta']
                if debug:
                    print(direction + " brightness calibration: " + str(bright_cal))
                if abs(med_bright - target_bright) > self.options[direction + '_bright_acceptable_error']:
                    if med_bright > target_bright:
                        #if debug:
                        #    print("Calibrating " + direction + ": too bright")
                        #setattr(curr_cal, direction + "_exposure",max(0, bright_cal - bright_delta))
                        #changed = True
                        changed = update_value(direction, "bright", -bright_delta, debug)
                    elif med_bright < target_bright and bright_cal < 100:
                        #if debug:
                        #    print("Calibrating " + direction + ": too dim")
                        #setattr(curr_cal, direction + "_exposure",min(100, bright_cal + bright_delta))
                        #changed = True
                        changed = update_value(direction, "bright", bright_delta, debug)
                    #shm.camera_calibration.set(curr_cal)
            if(self.options[direction+'_enable_color'] and self.options['enable']):
                red_cal = getattr(curr_cal, direction + "_red_gain")
                green_cal = getattr(curr_cal, direction + "_green_gain")
                blue_cal = getattr(curr_cal, direction + "_blue_gain")
                color_delta = self.options[direction + '_color_delta']
                curr_red = r[self.options[direction + '_red_y_pos']][self.options[direction + '_red_x_pos']]
                curr_green = g[self.options[direction + '_green_y_pos']][self.options[direction + '_green_x_pos']]
                curr_blue = b[self.options[direction + '_blue_y_pos']][self.options[direction + '_blue_x_pos']]

                color_cal_max = 100
                color_delta = self.options[direction + '_color_delta']
                if debug:
                    print(direction + " red calibration: " + str(red_cal))
                    print(direction + " green calibration: " + str(green_cal))
                    print(direction + " blue calibration: " + str(blue_cal))

                    print(direction + " current red: " + str(curr_red))
                    print(direction + " current green: " + str(curr_green))
                    print(direction + " current blue: " + str(curr_blue))

                accept_error = self.options[direction + '_color_acceptable_error']
                
                def get_val(c):
                    if c == 'red':
                        return curr_red
                    elif c == 'blue':
                        return curr_blue
                    else:
                        return curr_green
                def get_color(c):
                    if c == 'red':
                        return (255,0,0)
                    elif c == 'blue':
                        return (0,0,255)
                    else:
                        return (0,255,0)
                orders = ['red','green','blue']
                orders.sort(key=get_val)
                        
                if get_val(orders[2]) - accept_error > get_val(orders[1]):
                    if debug:
                        print("Calibrating " + direction + ": too" + orders[2])
                        draw_text(img,"too " + orders[2] + ": " + str(get_val(orders[2])-get_val(orders[1])),(20, 100),2,color=(0,0,0),thickness=2)
                    if orders[2] == 'red':
                        if red_cal > 0:
                            changed = changed or update_value(direction, 'red', -color_delta, debug)
                            #setattr(curr_cal, direction + "_red_gain",max(0,red_cal - color_delta))
                        elif green_cal < color_cal_max and blue_cal < color_cal_max:
                            changed = changed or update_value(direction, 'blue', color_delta, debug)
                            changed = changed or update_value(direction, 'green', color_delta, debug)
                            #setattr(curr_cal, direction + "_blue_gain",min(color_cal_max,blue_cal + color_delta))
                            #setattr(curr_cal, direction + "_green_gain",min(color_cal_max,green_cal + color_delta))
                    if orders[2] == 'green':
                        if green_cal > 0:
                            changed = changed or update_value(direction, 'green', -color_delta, debug)
                            #setattr(curr_cal, direction + "_green_gain",max(0,green_cal - color_delta))
                        elif red_cal < color_cal_max and blue_cal < color_cal_max:
                            changed = changed or update_value(diretion, 'red', color_delta, debug)
                            changed = changed or update_value(direction, 'blue', color_delta, debug)
                            #setattr(curr_cal, direction + "_red_gain",min(color_cal_max,red_cal + color_delta))
                            #setattr(curr_cal, direction + "_blue_gain",min(color_cal_max, blue_cal + color_delta))
                    if orders[2] == 'blue':
                        if blue_cal > 0:
                            changed = changed or update_value(direction, 'blue', -color_delta, debug)
                            #setattr(curr_cal, direction + "_blue_gain",max(0,blue_cal - color_delta))
                        elif red_cal < color_cal_max and green_cal < color_cal_max:
                            changed = changed or update_value(direction, 'red', color_delta, debug)
                            changed = changed or update_value(direction, 'green', color_delta, debug)
                            #setattr(curr_cal, direction + "_red_gain",min(color_cal_max,red_cal + color_delta))
                            #setattr(curr_cal, direction + "_green_gain",min(color_cal_max,green_cal + color_delta))
                    #changed = True
                else:
                    if debug:
                        draw_text(img,"low enough", (20,100),2,color=(0,0,0),thickness=2)
                if get_val(orders[0]) + accept_error < get_val(orders[1]):
                    if debug:
                        draw_text(img,"not " + orders[0] + " enough: " + str(get_val(orders[1]) - get_val(orders[0])),(20,400),2,color=(0,0,0),thickness=2)
                        print("Calibrating: " + direction + ": not" + orders[0] + "enough")
                    if orders[0] == 'red':
                        if red_cal < color_cal_max:
                            changed = changed or update_value(direction, 'red', color_delta, debug)
                            #setattr(curr_cal, direction + "_red_gain",min(color_cal_max, red_cal + color_delta))
                        elif green_cal > 0 and blue_cal > 0:
                            changed = changed or update_value(direction, 'green', -color_delta, debug)
                            changed = changed or update_value(direction, 'blue', -color_delta, debug)
                            #setattr(curr_cal, direction + "_green_gain",max(0,green_cal - color_delta))
                            #setattr(curr_cal, direction + "_blue_gain", max(0,blue_cal - color_delta))
                    if orders[0] == 'blue':
                        if blue_cal < color_cal_max:
                            changed = changed 
                            #setattr(curr_cal, direction + "_blue_gain",min(color_cal_max, blue_cal + color_delta))
                        elif red_cal > 0 and green_cal > 0:
                            setattr(curr_cal, direction + "_red_gain",max(0,red_cal - color_delta))
                            setattr(curr_cal, direction + "_green_gain", max(0, green_cal - color_delta))
                    if orders[0] == "green":
                        if green_cal < color_cal_max:
                            setattr(curr_cal, direction + "_green_gain",min(color_cal_max, green_cal + color_delta))
                        elif red_cal > 0 and blue_cal > 0:
                            setattr(curr_cal, direction + "_red_gain", max(0, red_cal - color_delta))
                            setattr(curr_cal, direction + "_blue_gain", max(0, blue_cal - color_delta))
                    changed = True
                else:
                    if debug:
                        draw_text(img, "high enough",(20,400),2,color=(0,0,0),thickness=2)
            self.post(direction + 'LAB L channel', lab_l)
            self.post(direction + 'R channel', r)
            self.post(direction + 'G channel', g)
            self.post(direction + 'B channel', b)
            self.post(direction + 'image', img)
if __name__ == '__main__':
    AutoCalibrate(['forward', 'downward'])()
