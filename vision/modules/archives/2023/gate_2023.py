#!/usr/bin/env python3
from vision.modules.ODJ_Vision.base import VisionProcessBase
from vision import options
from vision.framework.transform import elliptic_kernel, rect_kernel, morph_remove_noise, morph_close_holes, erode, dilate
from vision.framework.color import thresh_color_distance, bgr_to_gray, range_threshold
from vision.framework.feature import contour_area, min_enclosing_circle, min_enclosing_rect, contour_centroid, outer_contours, all_contours
import shm
import math
from vision.modules.ODJ_Vision.helpers import is_reflection
from vision.framework.draw import draw_contours, draw_line, draw_circle

import cv2
import numpy as np

module_options = [
    options.IntOption('brightness_max', 150, 0, 255)
]

def rect_ratio(contour):
    x, y, w, h = cv2.boundingRect(contour)
    return h/w

def find_vertical_rect(contour):
    rect = min_enclosing_rect(contour)

    # If rotation is between 45 and 135 degrees, then it's a vertical rectangle
    if (rect[2] > 45 and rect[2] < 135) or (rect[2] < -45 and rect[2] > -135):
        return rect[1][0] / rect[1][1]
    else:
        return rect[1][1] / rect[1][0]

def rect_ratio_err(contour):
    _, (w, h), _ = min_enclosing_rect(contour)
    max_, min_ = max(w, h), min(w, h)
    return max_ / min_

def area_circle(contour):
    return 3.1415926 * min_enclosing_circle(contour)[1]**2 / (contour_area(contour))

filters_list = [
    (lambda x: contour_area(x) >= 300),
    (lambda x: False if contour_area(x) == 0 else area_circle(x) > 2),
    (lambda x: rect_ratio(x) > 2),
    (lambda x: rect_ratio_err(x) > 3)
]


class CompGateVision(VisionProcessBase):
    """
    A structured model for finding a 2023 comp gate.
    """

    reflection_list = []

    status = 0
    """
    Determines the status of the gate. Because there are multiple visibility components,
    this is used instead of self.is_visible.
    
    0 - not visible                     \n
    1 - left and middle bars visible    \n
    2 - right and middle bars visible   \n
    3 - all bars visible                \n
    4 - left and right bars visible
    """
    def color_filter(self, img):
        self.w, self.h, _ = img.shape
        self.post("original", img)
        b, g, r = cv2.split(img)
        b_avg, g_avg, r_avg = np.average(img, axis=(0, 1))
        b_ratio = r_avg / b_avg
        g_ratio = r_avg / g_avg
        
        print(r_avg, g_avg, b_avg)
        print("avg:", (r_avg + g_avg + b_avg) / 3)

        def legacy_color():
            # constant to be multiplied to ratio for red. generally, low quality ~ 0.6, high quality ~ 1.5
            median = list(sorted([r_avg, g_avg, b_avg]))[1]
            const = max(1, 1 + 2 * math.log10((median / 60)))
            const = min(1.5, const)
            

            # brightness_min 
            mini = r_avg / 1.2
            maxi = (median + 255) / 2
            print("constant:", const)
            print("min:", mini)
            print("max:", maxi)
            
            final_b_ratio = max(1, b_ratio * const)
            final_g_ratio = max(1, g_ratio * const)

            print("b_ratio:", str(final_b_ratio))
            print("g_ratio:", str(final_g_ratio))

            binary_image = np.zeros_like(img)
            binary_image[((r > mini) &
                        ((r > final_b_ratio * b) |
                        (r > final_g_ratio * g)) &
                        (b < 250) &
                        (g < 250)
                        )
                        ] = [255, 255, 255]
            binary_image = bgr_to_gray(binary_image)[0]
            self.post('redness', binary_image)

            gray_image = bgr_to_gray(img)[0]
            
            self.post('gray', gray_image)
            gray_image = range_threshold(gray_image, 0, (median + 255 * 2) / 3)
            gray_image = erode(gray_image, elliptic_kernel(11))
            self.post('light remover', gray_image)

            final_image = binary_image & gray_image
            # self.post('combined red and gray', final_image)
            final_image = dilate(final_image, elliptic_kernel(5))
            # self.post('close holes', final_image)
            final_image = morph_remove_noise(final_image, elliptic_kernel(3))
            # self.post('remove noise', final_image)
            
            self.post('final_image', final_image)
            self.clist = outer_contours(final_image)
            pass
        
        legacy_color()


    def higher_process(self, img):
        print()
        """
        Requires two three long contours, both standing upright.
        Ordered by x-coordinate.

        Requires: clist is updated

        Effect: updates clist_final. Updates clist_draw.
        """
        self.reflection_list = []
        
        def valid_x_distance(first, second):
            length1 = abs(max(min_enclosing_rect(first)[1][1], min_enclosing_rect(first)[1][0]) / (self.w))
            length2 = abs(max(min_enclosing_rect(second)[1][1], min_enclosing_rect(second)[1][0]) / (self.w))
            length = (length1 + length2) / 2
            (x1, y1), (x2, y2) = self.normalized(contour_centroid(first)), self.normalized(contour_centroid(second))
            print("distance", str(abs(x1 - x2)))
            print("length", str(length))
            return abs(x1 - x2) > 2 * length * 0.7 and abs(x1 - x2) < 2 * length * 1.4
            pass

        def valid_y_distance_right(first, second):
            (x1, y1), (x2, y2) = self.normalized(contour_centroid(first)), self.normalized(contour_centroid(second))
            return abs(y1 - y2) < 0.05

        def similar_x(first, second, distance):
            diff = (self.normalized(contour_centroid(first))[0] - self.normalized(contour_centroid(second))[0])
            return abs(diff) - distance < 0

        def similar_size(first, second):
            r1, r2 = min_enclosing_circle(first)[1], min_enclosing_circle(second)[1]
            r1 = (r1 / self.w)
            r2 = (r2 / self.w)
            
            higher, lower = max(r1, r2), min(r1, r2)
            return higher / lower < 1.5
            
        def partial_eval():
            self.clist = sorted(self.clist, key = lambda x: contour_centroid(x)[0])
            self.clist_final = self.clist[:2]
            if similar_x(self.clist[0], self.clist[1], 0.04):
                print("reflection spotted")
                reflection = self.clist[0] if self.normalized(contour_centroid(self.clist[0]))[1] < self.normalized(contour_centroid(self.clist[1]))[1] else self.clist[1]
                self.clist_final = []
                self.reflection_list = [reflection]
                self.status = 0
            else:
                # check distance between the two
                length = abs(max(min_enclosing_rect(self.clist[0])[1][1], min_enclosing_rect(self.clist[0])[1][0]) / (self.w))
                (x1, y1), (x2, y2) = self.normalized(contour_centroid(self.clist[0])), self.normalized(contour_centroid(self.clist[1]))
                print("length", str(length))
                print("x1", str(x1))
                print("x2", str(x2))
                if abs(x1 - x2) > 3.5 * length and abs(x1 - x2) < 4.5 * length:
                    print("split action")
                    self.status = 4
                else:
                    l, w = min_enclosing_rect(self.clist[0])[1]
                    height = max(l, w)
                    if contour_centroid(self.clist[0])[1] - contour_centroid(self.clist[1])[1] > height * 0.60 and valid_x_distance(self.clist[0], self.clist[1]):
                        print("left")
                        self.status = 1
                    elif valid_x_distance(self.clist[0], self.clist[1]) and valid_y_distance_right(self.clist[0], self.clist[1]):
                        print("right")
                        self.status = 2
                    else:
                        print("does not pass")
                        self.clist_final = []
                        self.status = 0
            pass

        if len(self.clist) < 2: # 0 or 1 contours is not visible.
            self.status = 0
        elif len(self.clist) == 2: # 2 contours could be partially visible.
            partial_eval()
        else: # 3+ contours requires more processing.
            # reflection filter
            self.clist = sorted(self.clist, key=lambda x: contour_centroid(x)[0])
            heuristic_list = []
            for i in range(len(self.clist) - 2, -1, -1):
                refl, con = is_reflection(self.clist[i], self.clist[i+1], self, heuristic_list, tolerance=0.3)
                if refl:
                    reflection = self.clist.pop(i + con)
                    self.reflection_list.append(reflection)
                    print("reflection spotted")
            # reassess the length of self.clist after reflection filtering
            if len(self.clist) >= 3:
                self.clist_final = self.clist[:3]
                self.status = 3
            elif len(self.clist) == 2:
                partial_eval()
            else:
                self.status = 0
        
        # final check:
        self.draw_param()

    # def higher_process_exp(self, img):
    #     def local_search(contour, color):
    #         d = abs(max(min_enclosing_rect(contour)[1][1], min_enclosing_rect(contour)[1][0]))
    #         x, y = contour_centroid(contour)
    #         xi, yi = int(x), int(y)
    #         left = [(int(x + 2*d), int(y - d)), (int(x + 4*d), int(y - d))]
    #         draw_line(img, left[0], left[1], color, thickness=1)
    #         draw_line(img, (xi, yi), left[0], color, thickness=1)
    #         middle = [(int(x + 2*d), int(y)), (int(x - 2*d), int(y + d))]
    #         draw_line(img, middle[1], (xi, yi), color, thickness=1)
    #         draw_line(img, (xi, yi), middle[0], color, thickness=1)
    #         right = [(int(x - 2*d), int(y)), (int(x - 4*d), int(y + d))]
    #         draw_line(img, (xi, yi), right[0], color, thickness=1)
    #         draw_line(img, right[0], right[1], color, thickness=1)
    #         const = 0.67
    #         for e in left:
    #             draw_circle(img, e, int(const * d), color, 1)
    #         for e in middle:
    #             draw_circle(img, e, int(const * d), color, 1)
    #         for e in right:
    #             draw_circle(img, e, int(const * d), color, 1)

    #     colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
            
    #     for i in range(len(self.clist)):
    #         local_search(self.clist[i], colors[i])
        
    #     pass
    
    def draw_param(self):
        # LMR
        def right_adjust(contour):
            right = contour
            right_len = max(min_enclosing_rect(right)[1][0], min_enclosing_rect(right)[1][1])
            right_adj = contour_centroid(right)
            right_adj = (int(right_adj[0]), int(right_adj[1] + right_len))
            return right_adj
        if self.status == 4:
            self.clist_draw["L"] = contour_centroid(self.clist_final[0])
            self.clist_draw["R"] = right_adjust(self.clist_final[1])

        if self.status == 3:
            self.clist_draw["L"] = contour_centroid(self.clist_final[0])
            self.clist_draw["M"] = contour_centroid(self.clist_final[1])
            self.clist_draw["R"] = right_adjust(self.clist_final[2])
            self.clist_draw["left"] = ((self.clist_draw["L"][0] + self.clist_draw["M"][0])//2, self.clist_draw["L"][1])
            self.clist_draw["right"] = ((self.clist_draw["R"][0] + self.clist_draw["M"][0])//2, self.clist_draw["R"][1])
            pass
        # MR
        elif self.status == 2:
            self.clist_draw["M"] = contour_centroid(self.clist_final[0])
            self.clist_draw["R"] = right_adjust(self.clist_final[1])
            self.clist_draw["right"] = ((self.clist_draw["R"][0] + self.clist_draw["M"][0])//2, self.clist_draw["R"][1])
            pass
        # LM
        elif self.status == 1:
            self.clist_draw["L"] = contour_centroid(self.clist_final[0])
            self.clist_draw["M"] = contour_centroid(self.clist_final[1])
            self.clist_draw["left"] = ((self.clist_draw["L"][0] + self.clist_draw["M"][0])//2, self.clist_draw["L"][1])
            pass
        else:
            pass
    
    def shm(self):

        results = shm.gate_vision.get()

        left = None
        middle = None
        right = None

        if self.status == 4:
            left = self.clist_final[0]
            right = self.clist_final[1]
        
        elif self.status == 3:
            left = self.clist_final[0]
            middle = self.clist_final[1]
            right = self.clist_final[2]

        elif self.status == 2:
            middle = self.clist_final[0]
            right = self.clist_final[1]

        elif self.status == 1:
            left = self.clist_final[0]
            middle = self.clist_final[1]

        elif self.status == 0:
            results.leftmost_visible = 0
            results.middle_visible = 0
            results.rightmost_visible = 0
        
        if left is not None:
            results.leftmost_x, results.leftmost_y = self.normalized(contour_centroid(left))
            results.leftmost_len = abs(max(min_enclosing_rect(left)[1][1], min_enclosing_rect(left)[1][0]) / (self.w))
            results.leftmost_visible = 1
        else:
            results.leftmost_visible = 0
        
        if middle is not None:
            results.middle_x, results.middle_y = self.normalized(contour_centroid(middle))
            results.middle_len = abs(max(min_enclosing_rect(middle)[1][1], min_enclosing_rect(middle)[1][0]) / (self.w))
            results.middle_visible = 1
        else:
            results.middle_visible = 0
               
        if right is not None:
            right_len = abs(max(min_enclosing_rect(right)[1][1], min_enclosing_rect(right)[1][0]) / (self.w))
            right_coord = contour_centroid(right)
            right_coord = (right_coord[0], right_coord[1] + right_len)
            right_coord = self.normalized(right_coord)

            results.rightmost_x = right_coord[0]
            results.rightmost_y = right_coord[1]
            results.rightmost_len = right_len
            results.rightmost_visible = 1
        else:
            results.rightmost_visible = 0

        results.img_height = self.status
        shm.gate_vision.set(results)
        pass

        
        # total = 0
        # count = 0
        # if shm.gate_vision.leftmost_visible.get():
        #     total += shm.gate_vision.leftmost_len.get()
        #     count += 1
        # if shm.gate_vision.rightmost_visible.get():
        #     total += shm.gate_vision.rightmost_len.get()
        #     count += 1
        # if count == 0:
        #     print('n/a')
        # else:
        #     avg = total / count
        #     print(avg)
    
    def draw(self, img):
        super().draw(img)
        draw_contours(img, self.reflection_list, (0, 255, 255),
                      3)  # contours past filters are con
            
        pass

if __name__ == '__main__':
    CompGateVision("forward", options=module_options,
                   filters=filters_list)()

        
