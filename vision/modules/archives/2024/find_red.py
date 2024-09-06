#!/usr/bin/env python3
from vision.modules.base import ModuleBase
from vision import options
from vision.framework.draw import draw_text
from vision.framework.color import bgr_to_lab
from vision.framework.color import bgr_to_hsv
from vision.framework.color import range_threshold
from vision.framework.draw import draw_contours
from vision.framework.draw import draw_circle
from vision.framework.feature import outer_contours
from vision.framework.transform import erode
from vision.framework.transform import dilate
from vision.framework.transform import rect_kernel
from vision.framework.transform import elliptic_kernel
from vision.framework.feature import contour_centroid
from vision.framework.feature import contour_area
from vision.framework.feature import min_enclosing_circle
from vision.framework.color import white_balance_bgr, white_balance_bgr_blur
import shm
import math


# module_options = [
#   options.BoolOption("Hue Inverse", True),
#   options.IntOption('hsv_h_thresh_min', 10, 0, 180),
#   options.IntOption('hsv_h_thresh_max', 172, 0, 180),
#   options.IntOption('hsv_s_thresh_min', 45, 0, 255),
#   options.IntOption('hsv_s_thresh_max', 255, 0, 255),
#   options.IntOption('hsv_v_thresh_min', 50, 0, 255),
#   options.IntOption('hsv_v_thresh_max', 255, 0, 255),
# ]

module_options = [
  options.BoolOption("Hue Inverse", True),
  options.IntOption('hsv_h_thresh_min', 9, 0, 180),
  options.IntOption('hsv_h_thresh_max', 170, 0, 180),
  options.IntOption('hsv_s_thresh_min', 80, 0, 255),
  options.IntOption('hsv_s_thresh_max', 255, 0, 255),
  options.IntOption('hsv_v_thresh_min', 90, 0, 255),
#   CHANGED
  options.IntOption('hsv_v_thresh_max', 255, 0, 255),
]

class RedBuoy(ModuleBase):

    def filter_contours_by_size(self,contours,size_thresh=100):
        filtered_contours = []
        for i in range(len(contours)):
            if contour_area(contours[i]) > size_thresh:
                filtered_contours.append(contours[i])

        return filtered_contours

    def choose_contour(self,contours, size_thresh=100,circularity_thresh=0.5):
        print('choosing contours')
        if contours == None:
            print('no contours')
            return
        if len(contours) == 0:
            return
        circularity_sorted = self.circularity_sorted(contours) 
        
        print(len(circularity_sorted))
        for i in range(len(circularity_sorted)):
            print('lalalala')
            circularity,cont = circularity_sorted[i]
            print('cont area',contour_area(cont))
            print('circularity',circularity)
            if (circularity > circularity_thresh) and (contour_area(cont) > size_thresh):
                return cont

        return None


    def circularity_sorted(self, contours):
        print('sorting by circularity')
        circularity= []
        contours_list = []
        for i in range(len(contours)):
            area =  contour_area(contours[i])
            (circle_x,circle_y),rad =  min_enclosing_circle(contours[i])
            if rad:
                print('if there is rad', 'true')
                circularity.append(area/(math.pi * rad**2))
                contours_list.append(contours[i])
        circularity_and_contours = sorted(zip(circularity, contours_list), key=lambda zipped: zipped[0],reverse=True)

        return circularity_and_contours


    def process_img(self,img):
        img = white_balance_bgr_blur(img, 500)
        self.post('blurred',img)

        hsv,hsv_split = bgr_to_hsv(img)
        hsv_h, hsv_s, hsv_v = hsv_split
        self.post("hello", hsv_h)

        hsv_h_threshed = range_threshold(hsv_h, self.options['hsv_h_thresh_min'],self.options['hsv_h_thresh_max'])
        if self.options['Hue Inverse']:
            hsv_h_threshed = ~hsv_h_threshed
        
        hsv_s_threshed = range_threshold(hsv_s, self.options['hsv_s_thresh_min'],self.options['hsv_s_thresh_max'])
        hsv_v_threshed = range_threshold(hsv_v, self.options['hsv_v_thresh_min'],self.options['hsv_v_thresh_max'])

        self.post('threshed HSV H', hsv_h_threshed)
        self.post('threshed HSV S', hsv_s_threshed)
        self.post('threshed HSV V', hsv_v_threshed)


        combination = hsv_h_threshed & hsv_s_threshed & hsv_v_threshed
        self.post('combination', combination)

        dilated = dilate(combination,elliptic_kernel(3))
        eroded = erode(dilated,elliptic_kernel(5))
        dilated = dilate(eroded, elliptic_kernel(11))
        eroded = erode(dilated, elliptic_kernel(1))
        dilated = dilate(eroded, elliptic_kernel(13))

        return dilated

    def remove_in_x_range(self, x_and_contours,x_range,current_index,size_sim_thresh,all_contours):
        g = current_index +1
        l = current_index -1
        x = x_and_contours[current_index][0]
        contour = x_and_contours[current_index][2]
        contours_to_delete = []
        contours_to_keep = []

        while(g<len(x_and_contours) and (x_and_contours[g][0] - x) < x_range):
            if size_sim_thresh > min(contour_area(contour)/contour_area(x_and_contours[g][2]),contour_area(x_and_contours[g][2])/contour_area(contour)):
                contours_to_delete.append(x_and_contours[g][2])
            g +=1
            
        while(l>=0 and (x - x_and_contours[l][0]) < x_range):
            if size_sim_thresh > min(contour_area(contour)/contour_area(x_and_contours[l][2]),contour_area(x_and_contours[l][2])/contour_area(contour)):
                contours_to_delete.append(x_and_contours[l][2])
            l-=1

        for cont in all_contours:
            if cont not in contours_to_delete:
                contours_to_keep.append(cont)
        return contours_to_keep

    def remove_reflections(self,contours,x_range = 100,size_sim_thresh=0.2):
        print('in remove reflections')
        print('num refl in', len(contours))
        if len(contours) <= 1:
            return contours
        pos_values = []
        x_values = []
        y_values = []
        contours_to_delete = []
        contours_to_keep = []
        id = []
        for i in range(len(contours)):
            (center_x,center_y),rad =  min_enclosing_circle(contours[i])
            pos_values.append((center_x,center_y))
            x_values.append(center_x)
            y_values.append(center_y)
            id.append(i)
        
        x_and_contours = sorted(zip(x_values, y_values, contours,id), key=lambda zipped: zipped[0])
        y_and_contours = sorted(zip(x_values, y_values, contours,id), key=lambda zipped: zipped[1],reverse=True)
        # x_values,y_values,contours = x_and_contours

        print('fadfasdfa')
        # x_values,y_values = positions
        i = 0
        # for x,y,contour in y_and_contours:
        while i < len(y_and_contours) and i >=0:
            print('len',len(y_and_contours))
            x = y_and_contours[i][0]
            contour = y_and_contours[i][2]
            id = y_and_contours[i][3]
            x_values_sorted,y_values_sorted_by_x,cont_sorted_x,id_sorted_x = zip(*x_and_contours)
            x_values_sorted_by_y,y_values_sorted,cont_sorted_y,id_sorted_y = zip(*y_and_contours)
            x_values_sorted = list(x_values_sorted)
            y_values_sorted = list(y_values_sorted)
            id_sorted_x = list(id_sorted_x)
            id_sorted_y = list(id_sorted_y)
            print('x_id_sorted', id_sorted_x)
            print('y_id_sorted', id_sorted_y)
            print('id',id)
            current_index = id_sorted_x.index(id)

            g = current_index +1
            l = current_index -1
            while(g<len(x_and_contours) and (x_and_contours[g][0] - x) < x_range):
                if size_sim_thresh < min(contour_area(contour)/contour_area(x_and_contours[g][2]),contour_area(x_and_contours[g][2])/contour_area(contour)):
                    print('here1')
                    # print('x_and_contours[g][2]',x_and_contours[g][2])

                    y_index = id_sorted_y.index(x_and_contours[g][3])
                    print('y index',y_index)
                    print('x index', g)
                    # print(len(x_and_contours))
                    del y_and_contours[y_index]
                    del x_and_contours[g]
                    del id_sorted_x[g]
                    del id_sorted_y[y_index]
                   
                else:
                    g +=1
                
            while(l>=0 and (x - x_and_contours[l][0]) < x_range):
                if size_sim_thresh < min(contour_area(contour)/contour_area(x_and_contours[l][2]),contour_area(x_and_contours[l][2])/contour_area(contour)):
                    print('here2')
                    y_index = id_sorted_y.index(x_and_contours[l][3])
                    print('y index',y_index)
                    print('l index', g)
                    # print(len(x_and_contours))
                    del y_and_contours[y_index]
                    del x_and_contours[l]
                    del id_sorted_x[l]
                    del id_sorted_y[y_index]
                    i -=1
                    # if x_and_contours[g][0] < y:
                    # contours_to_delete.append(x_and_contours[l][2])
                l-=1
            i+=1

        for x,y,contour,id in y_and_contours:
            # if cont not in contours_to_delete:
            contours_to_keep.append(contour)
        print('num of contours to keep: ',len(contours_to_keep))
        return contours_to_keep
        
    def process(self, img):
        results = shm.red_buoy_results.get()
        img_processed = self.process_img(img)
        contours = outer_contours(img_processed)
        # self.post('original',img)
        # draw_contours(img,contours,thickness = 10)
        # self.post('original with all contours', img)
        self.post('dilated', img_processed)
        # print('contours before filter by size: ',len(contours))

        contours_reduced = self.filter_contours_by_size(contours,size_thresh=400)
        draw_contours(img,contours_reduced,thickness = 10)
        self.post('dilated', img_processed)
        # print('contours after filter by size: ',len(contours))

        contours_removed_reflections = self.remove_reflections(contours_reduced)
        # contours_removed_reflections = contours_reduced
        # draw_contours(img,contours,thickness = 10)
        draw_contours(img,contours_removed_reflections,color=(100,100,100),thickness = 10)
        self.post('after reflections', img)

        contour_chosen = self.choose_contour(contours_removed_reflections, 900,0.5)
        print('chosen contour area',contour_chosen)

        if contour_chosen is not None:
            print('TRUE')
            (center_x,center_y),rad =  min_enclosing_circle(contour_chosen)
            draw_circle(img, (int(center_x),int(center_y)),int(rad),(150,100,150),7)
            
            results.center_x = center_x
            results.center_y = center_y
            results.area = contour_area(contour_chosen)
            results.heuristic_score = contour_area(contour_chosen) * contour_area(contour_chosen)/(3.14*rad*rad)
            results.center_x,results.center_y = self.normalized((center_x,center_y))
            print('center_y',center_y)
            print('area_filled_ratio',results.area/(img.shape[0]*img.shape[1]))
        else:
            #    print("FALSE")
            results.heuristic_score = 0
        
        results.frame_height = img.shape[0]
        results.frame_width = img.shape[1]
        shm.red_buoy_results.set(results)


        self.post("original with contours", img)


if __name__ == '__main__':
  RedBuoy("forward", module_options)()
