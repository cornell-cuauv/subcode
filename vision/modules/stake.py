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
           options.DoubleOption('source_x_scale_upper_stake', 0.1, 0, 1),
           options.DoubleOption('source_y_scale_upper_stake', 0.1, 0, 1), 
           options.DoubleOption('source_x_scale_lower_stake', 0.1, 0, 1),
           options.DoubleOption('source_y_scale_lower_stake', 0.1, 0, 1), 
           options.DoubleOption('downsize_camera', 0.25, 0, 1),
           options.IntOption('min_match_count', 10, 0, 255),
           options.DoubleOption('good_ratio', 0.8, 0, 1),
           options.BoolOption('show_keypoints', False)]

PADDING = 50
BLUR_KERNEL = 3
BLUR_SD = 1

HEART = (1376, 514)
LEFT_CIRCLE = (390, 562)
RIGHT_CIRCLE = (1900, 570)

class Stake(ModuleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.orb = cv2.ORB_create(nfeatures=250, WTA_K=3)
        self.detector = cv2.xfeatures2d.SIFT_create()
        FLANN_INDEX_KDTREE = 0
        #FLANN_INDEX_LSH = 6
        index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5) #For SIFT
        # index_params= dict(algorithm = FLANN_INDEX_LSH,
        #            table_number = 12, #6, # 12
        #            key_size = 20, #12,     # 20
        #            multi_probe_level = 2) #1) #2 #For ORB
        search_params = dict(checks = 50)

        self.flann = cv2.FlannBasedMatcher(index_params, search_params)
        #self.flann = cv2.BFMatcher(normType=cv2.NORM_HAMMING2, crossCheck=False)
        #self.flann = cv2.BFMatcher()
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

        M = None

        try:
            matches = self.flann.knnMatch(des1,des2,k=2)
        except cv2.error as e:
            matches = []
            print(e)

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

            h,w = img1.shape
            pts = np.float32([ [PADDING,PADDING],[PADDING,h-1-PADDING],[w-1-PADDING,h-PADDING-1],[w-PADDING-1,PADDING] ]).reshape(-1,1,2)

            try:
                dst = cv2.perspectiveTransform(pts,M)
                area = cv2.contourArea(dst)
                rarea = cv2.minAreaRect(dst)
                rarea = rarea[1][0]*rarea[1][1]
                if area/rarea < RECTANGULARITY_THRESH: 
                    print("box lower than rectangularity threshold")
                    return output, None

                def e_length(pt1, pt2):
                    return ((pt1[0] - pt2[0])**2 + (pt1[1]-pt2[1])**2)**(0.5)

                def norm_length_diff(dst, line1, line2):
                    l1 = e_length(dst[line1[0]][0], dst[line1[1]][0])
                    l2 = e_length(dst[line2[0]][0], dst[line2[1]][0])
                    return (l2-l1)/min(l1, l2)

                shm.torpedoes_stake.align_h.set(norm_length_diff(dst, (0,1), (2,3)))
                shm.torpedoes_stake.align_v.set(norm_length_diff(dst, (0,2), (1,3)))
                #TODO: this runs for both boards even though only the lower board data is used for shm

                output = cv2.polylines(output,[np.int32(dst)],True,color,3, cv2.LINE_AA)
            except ZeroDivisionError:
                print('what')
            except cv2.error as e:
                print(e)

        else:
            print ("Not enough matches are found for %s - %d/%d" % (im1["name"], len(good),MIN_MATCH_COUNT))
            matchesMask = None
        return output, M

    
    def locate_source_point(self, image, mask, point, output=None):
        i = self.static[image]
        pt = np.float32([[[int(point[0]*i['rx'] + PADDING), int(point[1]*i['ry'] + PADDING)]]])
        pt = cv2.perspectiveTransform(pt, mask)
        draw_circle(output, tuple(pt[0][0]), 1, (0,0,255), thickness=3)
        return pt

    def process(self, *mats):
        print('start process')
        x = time.perf_counter()
        DOWNSIZE_CAMERA = self.options['downsize_camera']

        mat = cv2.cvtColor(mats[0], cv2.COLOR_BGR2GRAY)

        img2 = resize(to_umat(mat), int(mat.shape[1]*DOWNSIZE_CAMERA), int(mat.shape[0]*DOWNSIZE_CAMERA)) if DOWNSIZE_CAMERA else mat # trainImage

        upper_stake = self.static_process('upper_stake')
        lower_stake = self.static_process('lower_stake')

        # find the keypoints and descriptors with SIFT
        kp2, des2 = self.detector.detectAndCompute(img2,None)
        cam = {"img": img2, "kp":kp2, "des": des2}

        p = resize(mats[0], int(mats[0].shape[1] * self.options['downsize_camera']), int(mats[0].shape[0] * self.options['downsize_camera']))

        p, MU = self.match(upper_stake, cam, p, (255,0,0))
        p, ML = self.match(lower_stake, cam, p, (0, 255, 0))

        assert p is not None

        if self.options['show_keypoints']: p = cv2.drawKeypoints(p, kp2, None, (255,255,0))
        
        if MU is not None:
            shm.torpedoes_stake.open_hole_visible.set(True)
            left_hole = self.locate_source_point('upper_stake', MU, LEFT_CIRCLE, p)
            right_hole = self.locate_source_point('upper_stake', MU, RIGHT_CIRCLE, p)
            shm.torpedoes_stake.open_hole_x.set(self.normalized(right_hole[0][0][0], axis=0, mat=p))
            shm.torpedoes_stake.open_hole_y.set(self.normalized(right_hole[0][0][1], axis=1, mat=p))
            shm.torpedoes_stake.upper_visible.set(True)
        else:
            shm.torpedoes_stake.open_hole_visible.set(False)
            shm.torpedoes_stake.upper_visible.set(False)

        if ML is not None:
            shm.torpedoes_stake.heart_visible.set(True)
            heart = self.locate_source_point('lower_stake', ML, HEART, p)
            shm.torpedoes_stake.heart_x.set(self.normalized(heart[0][0][0], axis=0, mat=p))
            shm.torpedoes_stake.heart_y.set(self.normalized(heart[0][0][1], axis=1, mat=p))
            shm.torpedoes_stake.lower_visible.set(True)
        else:
            shm.torpedoes_stake.heart_visible.set(False)
            shm.torpedoes_stake.lower_visible.set(False)

        self.post("outline", p)
        print(time.perf_counter() - x)


if __name__ == '__main__':
    Stake('forward', opts)()
