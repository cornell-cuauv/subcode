#!/usr/bin/env python3

import sys
import cv2
import pickle
import numpy as np
from vision.framework.feature import outer_contours, contour_area

filename = sys.argv[1]
image = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
image = ~image
contour = max(outer_contours(image), key=contour_area)
pickled_contour = pickle.dumps(contour)
target_filename = filename.partition('.')[0] + '.pickle'
with open(target_filename, 'wb') as target:
    target.write(pickled_contour)

np.set_printoptions(suppress = True)
moments = cv2.moments(contour)
hu_moments = cv2.HuMoments(moments)
print(hu_moments)
