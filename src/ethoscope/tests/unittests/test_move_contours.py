import cv2
import numpy as np

# import the necessary packages
import argparse
import imutils

image = cv2.imread("../static_files/img/shapes_and_colors.jpg")
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, (5, 5), 0)
thresh = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY)[1]

cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
import ipdb; ipdb.set_trace()

cnts = imutils.grab_contours(cnts)
print(cnts.shape)

