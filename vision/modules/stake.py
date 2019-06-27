#!/usr/bin/env python3
import shm
import cv2

import time

import numpy as np
from vision.modules.base import ModuleBase, UndefinedModuleOption
from vision.framework.transform import resize, simple_gaussian_blur
from vision.framework.helpers import to_umat, from_umat
from vision.framework.draw import draw_circle

from vision import options

opts =    [options.DoubleOption('rectangular_thresh', 0.7, 0, 1),
           options.DoubleOption('source_x_scale_upper', 0.1, 0, 1),
           options.DoubleOption('source_y_scale_upper', 0.1, 0, 1), 
           options.DoubleOption('source_x_scale_lower', 0.1, 0, 1),
           options.DoubleOption('source_y_scale_lower', 0.1, 0, 1), 
           options.DoubleOption('downsize_camera', 0.25, 0, 1),
           options.IntOption('min_match_count', 10, 0, 255),
           options.DoubleOption('good_ratio', 0.8, 0, 1),
           options.BoolOption('show_keypoints', False),
           options.IntOption('board_separation', 300, 0, 4000),
           options.IntOption('board_horizontal_offset', 70, -1000, 1000),
           options.IntOption('lever_offset_x', -500, -3000, 3000),]
           # options.IntOption('lever_offset_y')]


PADDING = 50
BLUR_KERNEL = 3
BLUR_SD = 1

HEART = (1376, 514)
LEFT_CIRCLE = (390, 562)
RIGHT_CIRCLE = (1900, 570)

class Stake(ModuleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.detector = cv2.xfeatures2d.SIFT_create()
        FLANN_INDEX_KDTREE = 0
        index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5) #For SIFT
        search_params = dict(checks = 50)

        self.flann = cv2.FlannBasedMatcher(index_params, search_params)
        self.past_var = {"lever_origin_upper": np.zeros((5,2)), "lever_origin_lower": np.zeros((5,2))}
        self.static = {}

    def static_process(self, image):

        def find_key_descriptors(im):
            if self.options['source_x_scale_%s'%image] !=0 and self.options['source_y_scale_%s'%image] != 0:
                scaledim = resize(im, int(im.shape[1]*self.options['source_x_scale_%s'%image]), 
                                      int(im.shape[0]*self.options['source_y_scale_%s'%image]))
                scaledim = np.pad(scaledim, ((PADDING, PADDING), (PADDING, PADDING)), 'constant', constant_values=255)
                rx = self.options['source_x_scale_%s'%image]
                ry = self.options['source_y_scale_%s'%image]
            else:
                scaledim = im
                rx = 1
                ry = 1
            scaledim = simple_gaussian_blur(scaledim, BLUR_KERNEL, BLUR_SD)
            kp, des = self.detector.detectAndCompute(scaledim,None)
            self.static[image] = {"name": image, "org": im, 
                                  "img": scaledim, "rx": rx, "ry":ry, "kp":kp, "des":des}
            keypoints = cv2.drawKeypoints(scaledim.copy(), kp, None, (0,0,255), flags=0)
            self.post(image, keypoints)
            return self.static[image]

        if image in self.static:
            if self.static[image]['rx'] == self.options['source_x_scale_%s'%image] and \
                    self.static[image]['ry'] == self.options['source_y_scale_%s'%image]:
                return self.static[image]
            else: 
                im = self.static[image]["org"]
                return find_key_descriptors(im)
        else:
            im = cv2.imread('stake_images/%s.png'%image,0)

            assert im is not None
            return find_key_descriptors(im) 

    def match(self, im1, im2, output, color):
        MIN_MATCH_COUNT = self.options['min_match_count']
        RECTANGULARITY_THRESH = self.options['rectangular_thresh']
        kp1 = im1["kp"]
        kp2 = im2["kp"]
        des1 = im1["des"]
        des2 = im2["des"]
        img1 = im1["img"]
        img2 = im2["img"]

        try:
            matches = self.flann.knnMatch(des1,des2,k=2)
        except cv2.error as e:
            matches = []

        if output is None: output = img2

        # store all the good matches as per Lowe's ratio test.
        good = []
        for m,n in (x for x in matches if len(x) == 2) :
            if m.distance < self.options['good_ratio']*n.distance:
                good.append(m)

        if len(good)>MIN_MATCH_COUNT:
            src_pts = np.float32([ kp1[m.queryIdx].pt for m in good ]).reshape(-1,1,2)
            dst_pts = np.float32([ kp2[m.trainIdx].pt for m in good ]).reshape(-1,1,2)

            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC,5.0)
            matchesMask = mask.ravel().tolist()
            # print("m" + str(M))
            # print("ma" + str(mask))
            # print("mm" + str(matchesMask))

            h,w = img1.shape
            pts = np.float32([ [PADDING,PADDING],[PADDING,h-1-PADDING],[w-1-PADDING,h-PADDING-1],[w-PADDING-1,PADDING] ]).reshape(-1,1,2)

            try:
                dst = cv2.perspectiveTransform(pts,M)
                area = cv2.contourArea(dst)
                rarea = cv2.minAreaRect(dst)
                rarea = rarea[1][0]*rarea[1][1]
                if area/rarea < RECTANGULARITY_THRESH: 
                    #print("box lower than rectangularity threshold")
                    return output, None 

                def e_length(pt1, pt2):
                    return ((pt1[0] - pt2[0])**2 + (pt1[1]-pt2[1])**2)**(0.5)

                def norm_length_diff(dst, line1, line2):
                    l1 = e_length(dst[line1[0]][0], dst[line1[1]][0])
                    l2 = e_length(dst[line2[0]][0], dst[line2[1]][0])
                    return (l2-l1)

                Moments = cv2.moments(dst)

                getattr(shm.torpedoes_stake, "%s_align_h"%im1["name"]).set(norm_length_diff(dst, (0,1), (2,3)))
                getattr(shm.torpedoes_stake, "%s_align_v"%im1["name"]).set(norm_length_diff(dst, (0,2), (1,3)))
                getattr(shm.torpedoes_stake, "%s_size"%im1["name"]).set(area)
                getattr(shm.torpedoes_stake, "%s_center_x"%im1["name"]).set(Moments["m10"]/Moments['m00'])
                getattr(shm.torpedoes_stake, "%s_center_y"%im1["name"]).set(Moments["m01"]/Moments['m00'])

                output = cv2.polylines(output,[np.int32(dst)],True,color,3, cv2.LINE_AA)

                return output, M
            except ZeroDivisionError:
                print('what')
            except cv2.error as e:
                print(e)

        else:
            #print ("Not enough matches are found for %s - %d/%d" % (im1["name"], len(good),MIN_MATCH_COUNT))
            matchesMask = None
        return output, None

    
    def locate_source_point(self, image, mask, point, output=None, color=(0,0,255)):
        i = self.static[image]
        pt = np.float32([[[int(point[0]*i['rx'] + PADDING), int(point[1]*i['ry'] + PADDING)]]])
        print(mask)
        pt = cv2.perspectiveTransform(pt, mask)
        draw_circle(output, tuple(pt[0][0]), 1, color, thickness=3)
        return pt

    def process(self, *mats):
        x = time.perf_counter()
        DOWNSIZE_CAMERA = self.options['downsize_camera']

        mat = cv2.cvtColor(mats[0], cv2.COLOR_BGR2GRAY)

        img2 = resize(to_umat(mat), int(mat.shape[1]*DOWNSIZE_CAMERA), int(mat.shape[0]*DOWNSIZE_CAMERA)) if DOWNSIZE_CAMERA else mat # trainImage

        upper_stake = self.static_process('upper')
        lower_stake = self.static_process('lower')

        # find the keypoints and descriptors with SIFT
        kp2, des2 = self.detector.detectAndCompute(img2,None)
        cam = {"img": img2, "kp":kp2, "des": des2}

        p = resize(mats[0], int(mats[0].shape[1] * self.options['downsize_camera']), int(mats[0].shape[0] * self.options['downsize_camera']))

        p, MU = self.match(upper_stake, cam, p, (255,0,0))
        p, ML = self.match(lower_stake, cam, p, (0, 255, 0))

        assert p is not None

        self.post_shm(p, ML, MU)
        self.post("outline", p)
        #print(time.perf_counter() - x)

    def post_shm(self, p, ML, MU):
        shm.torpedoes_stake.camera_x.set(p.shape[1]//2)
        shm.torpedoes_stake.camera_y.set(p.shape[0]//2)

        if self.options['show_keypoints']: p = cv2.drawKeypoints(p, kp2, None, (255,255,0))
        
        if MU is not None:
            shm.torpedoes_stake.left_hole_visible.set(True)
            shm.torpedoes_stake.right_hole_visible.set(True)
            left_hole = self.locate_source_point('upper', MU, LEFT_CIRCLE, p)
            right_hole = self.locate_source_point('upper', MU, RIGHT_CIRCLE, p)
            shm.torpedoes_stake.left_hole_x.set(left_hole[0][0][0])
            shm.torpedoes_stake.left_hole_y.set(left_hole[0][0][1])
            shm.torpedoes_stake.right_hole_x.set(right_hole[0][0][0])
            shm.torpedoes_stake.right_hole_y.set(right_hole[0][0][1])
            shm.torpedoes_stake.upper_visible.set(True)

            lever_origin=(self.options['lever_offset_x'], self.static['upper']['org'].shape[1] + self.options['board_separation']//2)
            lever_origin_upper=self.locate_source_point('upper', MU, lever_origin, p, color=(255,0,255))
            shm.torpedoes_stake.lever_origin_x.set(lever_origin_upper[0][0][0])
            shm.torpedoes_stake.lever_origin_y.set(lever_origin_upper[0][0][1])
        else:
            shm.torpedoes_stake.left_hole_visible.set(False)
            shm.torpedoes_stake.right_hole_visible.set(False)
            shm.torpedoes_stake.upper_visible.set(False)
            if ML is not None:
                left_hole = (LEFT_CIRCLE[0] + self.options['board_horizontal_offset'], -self.options['board_separation']-self.static['upper']['org'].shape[0]+LEFT_CIRCLE[1])
                left_hole = self.locate_source_point('upper', ML, left_hole, p, color=(255,0,255))
                right_hole = (RIGHT_CIRCLE[0] + self.options['board_horizontal_offset'], -self.options['board_separation']-self.static['upper']['org'].shape[0]+RIGHT_CIRCLE[1])
                right_hole = self.locate_source_point('upper', ML, right_hole, p, color=(255,0,255))
                shm.torpedoes_stake.left_hole_x.set(left_hole[0][0][0])
                shm.torpedoes_stake.left_hole_y.set(left_hole[0][0][1])
                shm.torpedoes_stake.right_hole_x.set(right_hole[0][0][0])
                shm.torpedoes_stake.right_hole_y.set(right_hole[0][0][1])

        if ML is not None:
            shm.torpedoes_stake.heart_visible.set(True)
            heart = self.locate_source_point('lower', ML, HEART, p)
            #print(heart)
            shm.torpedoes_stake.heart_x.set(heart[0][0][0])
            shm.torpedoes_stake.heart_y.set(heart[0][0][1])
            shm.torpedoes_stake.lower_visible.set(True)

            lever_origin=(self.options['lever_offset_x'], -self.options['board_separation']//2)
            lever_origin_lower=self.locate_source_point('lower', ML, lever_origin, p, color=(0,0,0))
            shm.torpedoes_stake.lever_origin_x.set(lever_origin_lower[0][0][0])
            shm.torpedoes_stake.lever_origin_y.set(lever_origin_lower[0][0][1])
        else:
            shm.torpedoes_stake.heart_visible.set(False)
            shm.torpedoes_stake.lower_visible.set(False)
            if MU is not None:
                heart = (HEART[0] - self.options['board_horizontal_offset'], self.options['board_separation']+ self.static['upper']['org'].shape[0]+HEART[1])
                heart = self.locate_source_point('upper', MU, heart, p, color=(255,0,255))

        if ML is not None and MU is not None:
            # self.past_var['lever_origin_lower'] = np.roll(self.past_var['lever_origin_lower'], axis=1, shift=1)
            # self.past_var['lever_origin_lower'][0] = lever_origin_lower
            # self.past_var['lever_origin_upper'] = np.roll(self.past_var['lever_origin_upper'], axis=1, shift=1)
            # self.past_var['lever_origin_upper'][0] = lever_origin_upper
            # print("upper: {}, lower: {}".format(np.sum(np.var(np.linalg.norm(self.past_var['lever_origin_lower'], axis=0))), np.sum(np.var(np.linalg.norm(self.past_var['lever_origin_upper'], axis=0)))))
            # if np.sum(np.var(np.linalg.norm(self.past_var['lever_origin_lower']))) > np.sum(np.var(np.linalg.norm(self.past_var['lever_origin_upper']))):

            # covariance_u = np.cov(self.past_var['lever_origin_upper'])[1][0]
            # covariance_l = np.cov(self.past_var['lever_origin_lower'])[1][0]
            # if covariance_l > covariance_u:
            #     shm.torpedoes_stake.lever_origin_x.set(lever_origin_upper[0][0][0])
            #     shm.torpedoes_stake.lever_origin_y.set(lever_origin_upper[0][0][1])
            #     draw_circle(p, tuple(lever_origin_upper[0][0]), 1, (0,255,255), thickness=3)
            # else:
            #     shm.torpedoes_stake.lever_origin_x.set(lever_origin_lower[0][0][0])
            #     shm.torpedoes_stake.lever_origin_y.set(lever_origin_lower[0][0][1])
            #     draw_circle(p, tuple(lever_origin_lower[0][0]), 1, (0,255,255), thickness=3)

            # if lever_origin_upper[0][0][0] > lever_origin_lower[0][0][0]:
            #     shm.torpedoes_stake.lever_origin_x.set(lever_origin_upper[0][0][0])
            #     shm.torpedoes_stake.lever_origin_y.set(lever_origin_upper[0][0][1])
            #     draw_circle(p, tuple(lever_origin_upper[0][0]), 1, (0,0,255), thickness=3)
            # else:
            #     shm.torpedoes_stake.lever_origin_x.set(lever_origin_lower[0][0][0])
            #     shm.torpedoes_stake.lever_origin_y.set(lever_origin_lower[0][0][1])
            #     draw_circle(p, tuple(lever_origin_lower[0][0]), 1, (0,0,255), thickness=3)
            midpoint = np.multiply(np.add(lever_origin_lower[0][0],lever_origin_upper[0][0]), 0.5)
            shm.torpedoes_stake.lever_origin_x.set(midpoint[0])
            shm.torpedoes_stake.lever_origin_y.set(midpoint[1])
            draw_circle(p, tuple(midpoint), 1, (0,0,255), thickness=3)


if __name__ == '__main__':
    Stake('forward', opts)()
