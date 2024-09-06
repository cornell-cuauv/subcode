#!/usr/bin/env python3

from vision.modules.base import ModuleBase
from vision.framework.color import bgr_to_gray
import cv2, math, numpy as np

module_options = []

class MagicColor(ModuleBase):
    
    def process(self, img):
        def brightness(r, g, b):
            return 0.3 * r + 0.59 * g + 0.11 * b
        
        def offset(target, offset, factor=0.3, cut=1):
            rt, gt, bt = target
            ro, go, bo = offset

            return (int(((1 - factor) * rt + factor * ro) // cut),
                    int(((1 - factor) * gt + factor * go) // cut),
                    int(((1 - factor) * bt + factor * bo) // cut))
        
        rt, gt, bt = (255, 0, 0)
        brightness_target = brightness(rt, gt, bt)
        self.post("original", img)
        
        b_avg, g_avg, r_avg = np.average(img, axis=(0, 1))
        b_ratio = r_avg / b_avg
        g_ratio = r_avg / g_avg
        bg_ratio = b_avg / g_avg
        print("Median RGB values:", r_avg, g_avg, b_avg)
        print()
        print("b_ratio:", str(b_ratio))
        print("g_ratio:", str(g_ratio))
        print("bg_ratio:", str(bg_ratio))
        

        # constant to be multiplied to ratio for red. generally, low quality ~ 0.6, high quality ~ 1.5
        median = list(sorted([r_avg, g_avg, b_avg]))[1]
        const = 1 + 2 * math.log10((median / 90))
        print()
        print("constant:", const)

        # brightness_min 
        min = median / 6
        max = median / 1.1
        print()
        print("min:", min)
        print("max:", max)

        # the more different the background color is, the stronger the offset
        # not sure how the cut will look like?
        rf, gf, bf = offset((255, 0, 0), (r_avg, g_avg, b_avg), 0.2, 1.8)

        def custom_black_and_white(image_path, custom_function):
            # Load the image
            image = image_path
            b, g, r = cv2.split(image)

            # Apply the custom function to the entire image
            intensity = custom_function(r, g, b)

            # Create a white mask where the custom function returns True
            white_mask = np.where(intensity > 0, 255, 0)

            # Merge the intensity channel to create the black and white image
            black_white_image = cv2.merge((white_mask, white_mask, white_mask))
            return black_white_image

        # Example custom function: Average of RGB values
        def RGB_distance_thresh(r, g, b):
            threshold_red, threshold_green, threshold_blue = 30, 20, 20
            target_red, target_blue, target_green = 60, 30, 30

            # Calculate intensity using a weighted average (more weight to green)
             # Check if each channel value is within the target range
            list_of_params = [
                (r > min) &
                (r > g_ratio * const * g) &
                (r > b_ratio * const * b) &
                (g < max) &
                (b < max)
                ]
            # Return white (255) if all three channels are within the target range, otherwise return black (0)
            return np.where(list_of_params[0], 255, 0)
        
        binary_image = custom_black_and_white(img, RGB_distance_thresh)


        self.post("binary", binary_image)

if __name__ == '__main__':
    MagicColor("forward", options=module_options)()