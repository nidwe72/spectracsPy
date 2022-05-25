# further information:
# * http://stackoverflow.com/questions/11114349/how-to-visualize-descriptor-matching-using-opencv-module-in-python
# * http://docs.opencv.org/doc/tutorials/features2d/feature_homography/feature_homography.html#feature-homography
# * http://stackoverflow.com/questions/9539473/opencv-orb-not-finding-matches-once-rotation-scale-invariances-are-introduced
# * OpenCV 2 Computer Vision Application Programming Cookbook, Chapter 9
import cv2
import scipy as sp
import numpy as np
import time
from matplotlib import pyplot as plt

def sobel():
    img = cv2.imread('/home/nidwe/testPhilips.png')
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    #gray=equalize(gray)
    #gray = clahe(gray)

    cv2.imwrite('/home/nidwe/capture/equalize.jpg', gray)
    x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3, scale=1)
    y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3, scale=1)
    absx = cv2.convertScaleAbs(x)
    absy = cv2.convertScaleAbs(y)
    #edge = cv2.addWeighted(absx, 0.5, absy, 0.5, 0)
    edge = cv2.addWeighted(absx, 0.5, absy, 0.5, 0)
    #edge = equalize(edge)
    #edge = clahe(edge)
    cv2.imwrite('/home/nidwe/capture/sobel.jpg', edge)

    return edge

def canny(gray):
    edges=cv2.Canny(gray, 220, 250)
    cv2.imwrite('/home/nidwe/capture/canny.jpg', edges)


def equalize(img):
    equ = cv2.equalizeHist(img)
    return equ

def clahe(img):
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl1 = clahe.apply(img)
    return cl1

def hough(image):
    src =  cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Check if image is loaded fine

    dst = cv2.Canny(src, 50, 200, None, 3)

    # Copy edges to the images that will display the results in BGR

    lines = cv2.HoughLines(dst, 1, np.pi / 180, 150, None, 0, 0)

    index=0
    for line in lines:
        index=index+1
        if index==3:
            break
        for rho, theta in line:
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a * rho
            y0 = b * rho
            x1 = int(x0 + 2000 * (-b))
            y1 = int(y0 + 2000 * (a))
            x2 = int(x0 - 2000 * (-b))
            y2 = int(y0 - 2000 * (a))

            #cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.line(src, (x1, y1), (x2, y2), (255, 255, 255), 1)
    return src

sobel=sobel()

img = cv2.imread('/home/nidwe/capture/testPhilips.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

canny(sobel)

import time

start = time.time()
img = cv2.imread('/home/nidwe/capture/testPhilipsRotated5.png')
for i in range(1,100):
    # hough('/home/nidwe/capture/testPhilipsRotated.png','/home/nidwe/capture/hough.png')
    # hough('/home/nidwe/capture/testPhilipsRotated2.png','/home/nidwe/capture/hough2.png')
    # hough('/home/nidwe/capture/testPhilipsRotated3.png','/home/nidwe/capture/hough3.png')
    # hough('/home/nidwe/capture/testPhilipsRotated4.png','/home/nidwe/capture/hough4.png')
    hough(img)
end = time.time()
print("time")
print((end - start)/100)

img1_path = "/home/nidwe/Downloads/spec/testPhilipsCropped.png"
img2_path = "/home/nidwe/Downloads/spec/testPhilips.png"


img3_path = "/home/nidwe/testPhilips2.png"

img = cv2.imread(img3_path)
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)



#img1_path = "/home/nidwe/Downloads/spec/feature.png"
#img2_path = "/home/nidwe/Downloads/spec/haystack.png"

# test1 = cv2.imread(img1_path, 0)
# test2 = cv2.imread(img2_path, 0)
#
# orb = cv2.ORB_create()
#
# kp1 = orb.detect(test1, None)
# kp2 = orb.detect(test2, None)
#
# mark1 = cv2.drawKeypoints(test1, kp1, None, color=(0, 0, 255), flags=0)
# orient1 = cv2.drawKeypoints(test1, kp1, None, color=(0, 0, 255), flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
#
# mark2 = cv2.drawKeypoints(test2, kp2, None, color=(255, 0, 0), flags=0)
# orient2 = cv2.drawKeypoints(test2, kp2, None, color=(255, 0, 0), flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
#
# kp1, des1 = orb.compute(test1, kp1)
# kp2, des2 = orb.compute(test2, kp2)
#
# bf = cv2.BFMatcher(cv2.NORM_HAMMING)
# matches = bf.match(des1, des2)
#
# matches = sorted(matches, key=lambda x: x.distance)
# n=20
# result = cv2.drawMatches(mark1, kp1, mark2, kp2, matches[:min(n, len(matches))], None, matchColor=[0, 255, 0], flags=2)
#
# plt.imshow(result, interpolation='bicubic')
# plt.axis('off')
# plt.show()

