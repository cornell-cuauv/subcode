#!/usr/bin/env python2


import cv2
import numpy as np
mat = cv2.imread("roulette.png")
lab = cv2.cvtColor(mat, cv2.COLOR_BGR2LAB)
lab_split = cv2.split(lab)
cv2.imshow('lab', lab_split[1])
_ = cv2.waitKey()

threshed = cv2.inRange(lab_split[1], 200, 255)
threshed = cv2.erode(threshed, (5, 5))
cv2.imshow('threshed', threshed)
_ = cv2.waitKey()
contours = cv2.findContours(threshed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
for contour in contours:
    moments = cv2.moments(contour)
    cX = int(moments['m10'] / moments['m00'])
    cY = int(moments['m01'] / moments['m00'])
    cv2.drawContours(mat, [contour], -1, (0, 255, 0), 2)
    cv2.circle(mat, (cX, cY), 7, (255, 255, 255), -1)
    cv2.imshow('mat', mat)
    _ = cv2.waitKey()

threshed = cv2.inRange(lab_split[0], 0, 50)
threshed = cv2.erode(threshed, (5, 5), iterations=4)
cv2.imshow('threshed', threshed)
_ = cv2.waitKey()
contours = cv2.findContours(threshed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
for contour in contours:
    moments = cv2.moments(contour)
    cX = int(moments['m10'] / moments['m00'])
    cY = int(moments['m01'] / moments['m00'])
    cv2.drawContours(mat, [contour], -1, (0, 255, 0), 2)
    cv2.circle(mat, (cX, cY), 7, (255, 255, 255), -1)
    cv2.imshow('mat', mat)
    _ = cv2.waitKey()

threshed = cv2.inRange(lab_split[1], 0, 100)
threshed = cv2.erode(threshed, (5, 5))
cv2.imshow('threshed', threshed)
_ = cv2.waitKey()

edges = cv2.Canny(threshed, 100, 200)
cv2.imshow('edges', edges)
_ = cv2.waitKey()
lines = cv2.HoughLines(edges, 1, np.pi / 180, 70)
line_equations = []
for (i, (rho,theta)) in enumerate(lines[0][:2]):
    a = np.cos(theta)
    b = np.sin(theta)
    x0 = a*rho
    y0 = b*rho
    x1 = int(x0 + 1000*(-b))
    y1 = int(y0 + 1000*(a))
    x2 = int(x0 - 1000*(-b))
    y2 = int(y0 - 1000*(a))
    cv2.line(mat,(x1,y1),(x2,y2),(0,0,255),2)
    cv2.imshow('mat', mat)
    _ = cv2.waitKey()
    line_equations.append((float(x1), float(x2), float(y1), float(y2)))

[x01, x02, y01, y02] = line_equations[0]
[x11, x12, y11, y12] = line_equations[1]
b1 = (y02 - y01) / (x02 - x01)
b2 = (y12 - y11) / (x12 - x11)
intersection_x = int((b1 * x01 - b2 * x11 + y11 - y01) / (b1 - b2))
intersection_y = int(b1 * (intersection_x - x01) + y01)
cv2.circle(mat, (intersection_x, intersection_y), 7, (255, 255, 255), -1)
cv2.imshow('mat', mat)
_ = cv2.waitKey()

contours = cv2.findContours(threshed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
for contour in contours:
    moments = cv2.moments(contour)
    cX = int(moments['m10'] / moments['m00'])
    cY = int(moments['m01'] / moments['m00'])
    cv2.drawContours(mat, [contour], -1, (0, 255, 0), 2)
    cv2.circle(mat, (cX, cY), 7, (255, 255, 255), -1)
    cv2.imshow('mat', mat)
    _ = cv2.waitKey()
    translated_x = cX - intersection_x
    translated_y = cY - intersection_y
    predicted_x = translated_x * np.cos(np.radians(20)) - translated_y * np.sin(np.radians(20))
    predicted_y = translated_x * np.sin(np.radians(20)) + translated_y * np.cos(np.radians(20))
    predicted_x = int(predicted_x + intersection_x)
    predicted_y = int(predicted_y + intersection_y)
    cv2.circle(mat, (predicted_x, predicted_y), 7, (255, 0, 0), -1)
    cv2.imshow('mat', mat)
    _ = cv2.waitKey()
