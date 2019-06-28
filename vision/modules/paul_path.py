from math import radians, atan2, sqrt, sin, cos, atan

import cv2
import numpy as np
from vision.modules.base import ModuleBase
from vision.options import *
import math

#static_img = cv2.imread('path1.png')
static_img = None
opts = [
        #IntOption('l_min', 0, 0, 255),
        #IntOption('l_max', 255, 0, 255),
        #IntOption('a_min', 0, 0, 255),
        #IntOption('a_max', 255, 0, 255),
        #IntOption('b_min', 0, 0, 255),
        #IntOption('b_max', 255, 0, 255),
        IntOption('l_trg', 129, 0, 255), # 140
        IntOption('a_trg', 201, 0, 255),
        IntOption('b_trg', 183, 0, 255),
        IntOption('houghness', 104, 0, 200),
        IntOption('canny1', 128, 0, 1000), # 25
        IntOption('canny2', 298, 0, 1000), # 93
        IntOption('d_thresh', 47, 0, 255), # 128
]

kernel = np.ones((5, 5), np.uint8)


class Path(ModuleBase):
    def process(self, mat):
        self.post('img', mat)
        if static_img is not None: mat = static_img.copy()
        cc = cv2.cvtColor(mat, cv2.COLOR_BGR2LAB).astype(np.int16)
        z = np.abs(cc[:,:,0] - self.options['l_trg']) + \
            np.abs(cc[:,:,1] - self.options['a_trg']) + \
            np.abs(cc[:,:,2] - self.options['b_trg'])
        #z //= 3
        np.clip(z, 0, 255, out=z)
        z = z.astype(np.uint8)
        t2 = z < self.options['d_thresh']
        self.post('dist', z)
        edg = cv2.Canny(z, self.options['canny1'], self.options['canny2'], apertureSize=3)
        edg = cv2.dilate(edg, kernel)
        #edg = cv2.erode(edg, kernel)
        near_target = cv2.dilate(t2.astype(np.uint8) * 255, kernel, iterations=2)
        self.post('near_target', near_target)
        edg &= near_target
        self.post('edg', edg)
        lines = cv2.HoughLines(edg, 1, np.pi/180, self.options['houghness'])
        #print(lines)
        if lines is None: return
        #print(lines)
        if len(lines) < 2: return
        lines[lines[:,0,0] < 0,:,1] += np.pi
        lines[:,:,0] = np.abs(lines[:,:,0])
        pkv = np.exp(1j * lines[:,:,1])
        kvalues = (pkv ** 2).astype(np.complex64).view(np.float32)
        #kvalues = kv1
        #kvalues = np.hstack((kv1, lines[:,:,0] / 100))
        #kvalues = kvalues[:,np.newaxis,:]
        #print(kvalues)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        ret, label, center = cv2.kmeans(kvalues, 2, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        s = np.int64(sorted(range(2), key=lambda i: math.atan2(center[i][1], center[i][0])))
        center = center[s]
        label = s[label]
        #print(center)
        label = label[:,0]
        ll = []
        clrs = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 255, 0), (255, 0, 255), (0, 0, 128), (0, 128, 0), (128, 0, 0)]
        superlabels = label * 2
        supercenters = []
        m2 = mat.copy()
        for i in range(2):
            matches = lines[label == i,:,0]
            if len(matches) < 2: return
            r2, l2, c2 = cv2.kmeans(matches, 2, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            s2 = np.int64(sorted(range(2), key=lambda i: c2[i,0]))
            c2 = c2[s2]
            l2 = s2[l2]
            for j, in c2:
                supercenters.append((np.mean(pkv[label == i,0], axis=0), j))
            superlabels[label == i] += l2[:,0]

        #supercenters = np.float32(supercenters)
        d1 = (supercenters[0][0] + supercenters[1][0], (supercenters[0][1] + supercenters[1][1]) / 2)
        d2 = (supercenters[2][0] + supercenters[3][0], (supercenters[2][1] + supercenters[3][1]) / 2)
        # get intersection, split on middle of narrow wedge 
            
        for i, (v, dst) in enumerate((d1, d2)):
            v /= abs(v)
            ctr = v * dst
            vc = v * 1j
            p1 = ctr + 1000 * vc
            p2 = ctr - 1000 * vc
            mat = cv2.line(mat, (int(p1.real), int(p1.imag)), (int(p2.real), int(p2.imag)), clrs[i], 2)
        #print(supercenters)
        for i, ((r, th),) in enumerate(lines):
            #print(r, th)
            
            dr = np.exp(1j*th)
            cent = dr * r
            drx = dr * 1j
            #print(cent, end='\t')
            p1 = cent + 1000 * drx
            p2 = cent + -1000 * drx
            #print(p1, p2)
            #print(label[i])
            m2 = cv2.line(m2, (int(p1.real), int(p1.imag)), (int(p2.real), int(p2.imag)), clrs[superlabels[i]], 2)
        #print(angles)
        #l2 = np.complex64([np.exp(2j * th) for (r, th), in lines]
        #dirs = [dir ** 2 for cent, dir in ll]

        self.post('mat', mat)
        self.post('m2', m2)




if __name__ == '__main__':
    Path('downward', opts)()
