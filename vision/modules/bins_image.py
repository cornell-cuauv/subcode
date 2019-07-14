#!/usr/bin/env python3
import shm
import cv2
from functools import reduce
import traceback
import sys

# import time

import numpy as np
from vision.modules.base import ModuleBase  # , UndefinedModuleOption
from vision.framework.transform import resize, simple_gaussian_blur
from vision.framework.helpers import to_umat  # , from_umat
from vision.framework.draw import draw_circle
from vision.framework.color import bgr_to_lab, range_threshold


from vision import options

opts =    [options.DoubleOption('rectangular_thresh', 0.8, 0, 1),
           options.DoubleOption('source_x_scale_bat', 0.1, 0, 1),
           options.DoubleOption('source_y_scale_bat', 0.1, 0, 1),
           options.DoubleOption('source_x_scale_wolf', 0.1, 0, 1),
           options.DoubleOption('source_y_scale_wolf', 0.1, 0, 1),
           options.DoubleOption('camera_scale', 0.35, 0, 1),
           options.IntOption('min_match_count', 10, 0, 255),
           options.DoubleOption('good_ratio', 0.8, 0, 1),
           options.BoolOption('show_keypoints', False),
           options.IntOption('min_gray', 25, 0, 255),
            options.IntOption('l_trg', 71, 0, 255),
            options.IntOption('a_trg', 94, 0, 255),
            options.IntOption('b_trg', 164, 0, 255),
            options.IntOption('d_thresh', 96, 0, 255), # 128
#           options.IntOption('board_separation', 450, 0, 4000),
#           options.IntOption('board_horizontal_offset', 70, -1000, 1000),
#           options.IntOption('lever_position_x', -500, -3000, 3000),
#           options.IntOption('lever_position_y', 2500, 0, 6000),
#           options.IntOption('heart_offset_x', 0, -3000, 3000),
#           options.IntOption('heart_offset_y', 0, -3000, 3000),
#           options.IntOption('left_circle_offset_x', -60, -3000, 3000),
#           options.IntOption('left_circle_offset_y', -112, -3000, 3000),
#           options.IntOption('right_circle_offset_x', -148, -3000, 3000),
#           options.IntOption('right_circle_offset_y', -110, -3000, 3000),
#           options.IntOption('lever_l', 129, 0, 255),
#           options.IntOption('lever_a', 201, 0, 255),
#           options.IntOption('lever_b', 183, 0, 255),
#           options.IntOption('lever_color_distance', 50, 0, 255),
#           options.IntOption('contour_size_min', 5, 0, 1000),
#           options.IntOption('lever_endzone_left', 1793, 0, 6000),
#           options.IntOption('lever_gutter_top', 2238, 0, 6000),
#           options.IntOption('lever_gutter_bot', 2887, 0, 6000),
           ]


PADDING = 50
GUTTER_PAD = 500
BLUR_KERNEL = 7
BLUR_SD = 1

HEART = (1356, 3250)
LEFT_CIRCLE = (390, 562)
RIGHT_CIRCLE = (1900, 570)

MOVE_DIRECTION=1  # 1 if lever on left else -1 if on right
kernel = np.ones((5, 5), np.uint8)

class BinsImage(ModuleBase):

    def heart(self):
        return (HEART[0] + self.options['heart_offset_x'], HEART[1] + self.options['heart_offset_y'])
    def left_circle(self):
        return (LEFT_CIRCLE[0] + self.options['left_circle_offset_x'], LEFT_CIRCLE[1] + self.options['left_circle_offset_y'])
    def right_circle(self):
        return (RIGHT_CIRCLE[0] + self.options['right_circle_offset_x'], RIGHT_CIRCLE[1] + self.options['right_circle_offset_y'])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.detector = cv2.xfeatures2d.SIFT_create(contrastThreshold=.02)
        FLANN_INDEX_KDTREE = 0
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)  # For SIFT
        search_params = dict(checks=50)

        self.flann = cv2.FlannBasedMatcher(index_params, search_params)
        self.past_var = {"lever_origin_upper": np.zeros((5, 2)), "lever_origin_lower": np.zeros((5, 2))}
        self.static = {}


    def static_process(self, image1, name=None):
        if name is None: name = image1

        def find_key_descriptors(im):
            scaledim = resize(im, int(im.shape[1]*self.options['source_x_scale_%s' % image]),
                                  int(im.shape[0]*self.options['source_y_scale_%s' % image]))

            #mean = 0
            #sigma = 20
            #gauss = np.random.normal(mean,sigma,scaledim.shape)
            #scaledim = scaledim.astype(np.int16) + gauss.astype(np.int8)
            #np.clip(scaledim, 0, 255, out=scaledim)
            #scaledim = scaledim.astype(np.uint8)

            scaledim = np.pad(scaledim, ((PADDING, PADDING), (PADDING, PADDING)), 'constant', constant_values=255)
            rx = self.options['source_x_scale_%s' % image]
            ry = self.options['source_y_scale_%s' % image]
            scaledim = simple_gaussian_blur(scaledim, BLUR_KERNEL, BLUR_SD)
            kp, des = self.detector.detectAndCompute(scaledim, None)
            self.static[image] = {"name": image, "org": im,
                                  "img":  scaledim, "rx":  rx, "ry":  ry, "kp": kp, "des": des}
            keypoints = cv2.drawKeypoints(scaledim.copy(), kp, None, (0, 0, 255), flags=0)
            self.post(image, keypoints)
            return self.static[image]

        image = name

        if image in self.static:
            if self.static[image]['rx'] == self.options['source_x_scale_%s' % image] and \
                    self.static[image]['ry'] == self.options['source_y_scale_%s' % image]:
                return self.static[image]
            else:
                im1 = self.static[image]["org"]
                return find_key_descriptors(im1)
        else:
            im1 = cv2.imread('bins_images/%s.png' % image1, 0)
            self.static[image1] = {"org": im1}

            assert im1 is not None
            return find_key_descriptors(im1)


    def match(self, im1, im2, output, color, contour_segment, n_segs):
        MIN_MATCH_COUNT = self.options['min_match_count']
        RECTANGULARITY_THRESH = self.options['rectangular_thresh']
        kp1 = im1["kp"]
        kp2 = im2["kp"]
        des1 = im1["des"]
        des2 = im2["des"]
        img1 = im1["img"]
        img2 = im2["img"]

        try:
            matches = self.flann.knnMatch(des1, des2, k=2)
        except cv2.error as e:
            matches = []
            print(e)

        if output is None: output = img2

        # store all the good matches as per Lowe's ratio test.
        good = [m for (m, n) in matches if m.distance < self.options['good_ratio'] * n.distance]
        #pts = np.int0([x.pt for x in kp2])
        #labels = msk[pts]
        #good = [m for m in good if kp
        #good = []
        #for m, n in matches:#(x for x in matches if len(x) == 2):
        #    if m.distance < self.options['good_ratio']*n.distance:
        #        good.append(m)


        if len(good) > MIN_MATCH_COUNT:
            #matchesView = cv2.drawMatchesKnn(img1, kp1, img2, kp2, matches, None)
            #self.post('match_' + im1['name'], matchesView)
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

            lpts = np.int0(dst_pts)[:,0]
            #lpts = lpts[lpts[:,0] < contour_segment
            #print(lpts)
            lbs = contour_segment[lpts[:,1], lpts[:,0]]
            #print(lbs)
            #print(lbs.shape)
            if n_segs <= 1: return output, None
            msks = [lbs == i for i in range(1, n_segs)]
            mx = max(msks, key=lambda x: x.sum())
            #print(msks)
            #print(mx)
            src_pts = src_pts[mx]
            dst_pts = dst_pts[mx]
            g2 = [g for i, g in enumerate(good) if mx[i]]
            if mx.sum() == 0: return output, None
            #pts = np.int0([x.pt for x in kp2])
            #labels = msk[pts]

            #src_pts_2 = [kp1[m.queryIdx] for m in good]).reshape(-1, 1, 2)
            #dst_pts_2 = [kp2[m.trainIdx] for m in good]).reshape(-1, 1, 2)
            matchesView = cv2.drawMatches(img1, kp1, img2, kp2, good, None)
            self.post('match_' + im1['name'], matchesView)

            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 1.0)
            if M is None:
                print('No homography found', file=sys.stderr)
                return output, None
            g3 = [g2[i] for i, v in enumerate(mask) if v]
            matchesView2 = cv2.drawMatches(img1, kp1, img2, kp2, g3, None)
            self.post('inliers_' + im1['name'], matchesView2)
            # matchesMask = mask.ravel().tolist()
            # print("m" + str(M))
            # print("ma" + str(mask))
            # print("mm" + str(matchesMask))

            h, w = img1.shape
            pts = np.float32([[PADDING, PADDING], [PADDING, h-1-PADDING], [w-1-PADDING, h-PADDING-1], [w-PADDING-1, PADDING]]).reshape(-1, 1, 2)

            try:
                #print(pts, M)
                dst = cv2.perspectiveTransform(pts, M)
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
                    return (l2-l1)

                Moments = cv2.moments(dst)

                #getattr(shm.torpedoes_stake, "%s_align_h" % im1["name"]).set(norm_length_diff(dst, (0,1), (2,3)))
                ## getattr(shm.torpedoes_stake, " % s_align_v" % im1["name"]).set(norm_length_diff(dst, (0,2), (1,3)))
                #getattr(shm.torpedoes_stake, "%s_size" % im1["name"]).set(area)
                #getattr(shm.torpedoes_stake, "%s_center_x" % im1["name"]).set(Moments["m10"]/Moments['m00'])
                #getattr(shm.torpedoes_stake, "%s_center_y" % im1["name"]).set(Moments["m01"]/Moments['m00'])

                output = cv2.polylines(output, [np.int32(dst)], True, color, 3, cv2.LINE_AA)

                return output, M
            except ZeroDivisionError:
                print('Division by zero')
            except cv2.error as e:
                #traceback.print_exception(type(e), e)
                traceback.print_exc()
                #print(e)

        # else:
            # print ("Not enough matches are found for %s - %d/%d" % (im1["name"], len(good), MIN_MATCH_COUNT))
        return output, None


    def locate_source_point(self, image, mask, point, output=None, color=(0, 0, 255)):
        i = self.static[image]
        pt = np.float32([[[int(point[0]*i['rx'] + PADDING), int(point[1]*i['ry'] + PADDING)]]])
        # print(mask)
        pt = cv2.perspectiveTransform(pt, mask)
        draw_circle(output, tuple(pt[0][0]), 1, color, thickness=3)
        return pt


    def post_shm(self, mat, p, M):
        shm.torpedoes_stake.camera_x.set(p.shape[1]//2)
        shm.torpedoes_stake.camera_y.set(p.shape[0]//2)

        if M is not None:
            left_hole = self.locate_source_point('board', M, self.left_circle(), p)
            right_hole = self.locate_source_point('board', M, self.right_circle(), p)
            shm.torpedoes_stake.left_hole_x.set(left_hole[0][0][0])
            shm.torpedoes_stake.left_hole_y.set(left_hole[0][0][1])
            shm.torpedoes_stake.right_hole_x.set(right_hole[0][0][0])
            shm.torpedoes_stake.right_hole_y.set(right_hole[0][0][1])
            shm.torpedoes_stake.board_visible.set(True)

            lever_origin = (self.options['lever_position_x'], self.options['lever_position_y'])
            lever_origin_board = self.locate_source_point('board', M, lever_origin, p, color=(255, 0, 255))
            shm.torpedoes_stake.lever_origin_x.set(lever_origin_board[0][0][0])
            shm.torpedoes_stake.lever_origin_y.set(lever_origin_board[0][0][1])

            heart = self.locate_source_point('board', M, self.heart(), p)
            shm.torpedoes_stake.heart_x.set(heart[0][0][0])
            shm.torpedoes_stake.heart_y.set(heart[0][0][1])
        else:
            shm.torpedoes_stake.board_visible.set(False)

        shm.torpedoes_stake.lever_finished.set(self.lever_finished(mat, 'board', M, p))
        # print(self.lever_finished(mat, 'board', M, p))

    def process(self, *mats):
        # x = time.perf_counter()
        CAMERA_SCALE = self.options['camera_scale']

        mat = resize(mats[0], int(mats[0].shape[1]*CAMERA_SCALE), int(mats[0].shape[0]*CAMERA_SCALE)) if CAMERA_SCALE else mats[0]
        mm = mat.astype(np.int16)
        dst = np.abs(mm[:,:,0] - self.options['l_trg']) + \
            np.abs(mm[:,:,1] - self.options['a_trg']) + \
            np.abs(mm[:,:,2] - self.options['b_trg'])
        self.post('yellowness', (dst // 3).astype(np.uint8))
        np.clip(dst, 0, 255, out=dst)
        dst = dst.astype(np.uint8)
        res, yellow_mask = cv2.threshold(dst, self.options['d_thresh'], 255, cv2.THRESH_BINARY_INV)
        self.post('yellow_mask', yellow_mask)

        img2 = cv2.cvtColor(to_umat(mat), cv2.COLOR_BGR2GRAY)

        #img2 = resize(to_umat(mat), int(mat.shape[1]*camera_scale), int(mat.shape[0]*camera_scale)) if DOWNSIZE_CAMERA else mat  # trainImage

        bat = self.static_process('bat')
        wolf = self.static_process('wolf')

        #black_areas = img2 < self.options['min_gray']
        res, black_areas = cv2.threshold(img2, self.options['min_gray'], 255, cv2.THRESH_BINARY_INV)
        black_areas = cv2.erode(black_areas, kernel)
        black_areas = cv2.dilate(black_areas, kernel, iterations=2)
        self.post('black_areas', black_areas)
        img, contours, hierarchy = cv2.findContours(black_areas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        msk = np.zeros(mm.shape[:-1], dtype=np.uint8)
        #szcs = sorted(contours, key=cv2.contourArea, reverse=True)
        
        for i, x in enumerate(contours):#szcs[:2]:
            #pts = cv2.boxPoints(cv2.minAreaRect(x))
            #print(pts)
            #print(np.mean(pts, axis=0))
            #cv2.drawContours(msk, [np.int0((pts * 19 + np.mean(pts, axis=0)) / 20)], -1, 255, -1)
            mm = np.mean(x, axis=0)
            #print(x * 9 + mm, mm)
           # print(x)
            cv2.drawContours(msk, [np.int0((x * 2 + mm) / 3)], -1, i+1, -1)

        #for p in szcs[0:2]:
        #    msk = cv2.fillPoly(msk, p, 255)
        colors = np.uint8([(0, 0, 0), (0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 255, 0), (255, 0, 255), (255, 255, 255)])
        self.post('blk_fill', colors[np.clip(msk, 0, 7)])
                

        #print(szcs)
        #black_areas = black_areas.astype(np.uint8)
        #target_area = cv2.dilate(black_areas, kernel, iterations=10)
        #target_area = target_area.get()
        #self.post('target_area', target_area)

        #target_area = cv2.erode(yellow_mask, kernel)
        #target_area = cv2.dilate(target_area, kernel, iterations=10)
        #target_area &= msk
        target_area = msk
        #self.post('target_area', target_area)

        # find the keypoints and descriptors with SIFT

        #img2 = cv2.UMat(np.pad(img2.get(), ((PADDING, PADDING), (PADDING, PADDING)), 'constant', constant_values=255)) # boo
        kp2, des2 = self.detector.detectAndCompute(img2, None)
        #cv2.UMat(des2, [0, 1, 2])
        #print(dir(des2))
        #print(des2.get([0, 1, 2]))
        #print(kp2)
        #print(max(x.pt[1] for x in kp2))
        #print(max(x.pt[0] for x in kp2))
        p = resize(mats[0], int(mats[0].shape[1] * self.options['camera_scale']), int(mats[0].shape[0] * self.options['camera_scale']))
        if self.options['show_keypoints']:
            p = cv2.drawKeypoints(p, kp2, None, (0, 255, 255))
        #print([x.pt for x in kp2])
        idxs = [i for (i, x) in enumerate(kp2) if (0 < x.pt[1] < target_area.shape[0]) and (0 < x.pt[0] < target_area.shape[1]) and target_area[int(x.pt[1]), int(x.pt[0])]]
        kp2 = [kp2[i] for i in idxs]
        des2 = cv2.UMat(des2.get()[idxs])
        #print(kp2[0].pt)
        cam = {"img": img2, "kp": kp2, "des": des2}

        if self.options['show_keypoints']:
            p = cv2.drawKeypoints(p, kp2, None, (255, 255, 0))
        p_mat = p.copy()

        p, M1 = self.match(bat, cam, p, (0, 0, 255), msk, len(contours))
        p, M2 = self.match(wolf, cam, p, (0, 255, 0), msk, len(contours))

        assert p is not None

        #try:
        #    self.post_shm(p_mat, p, M)
        #except cv2.error as e:
        #    print(e)

        self.post("outline", p)

        # print(time.perf_counter() - x)



if __name__ == '__main__':
    BinsImage('downward', opts)()
