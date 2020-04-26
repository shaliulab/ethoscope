import cv2
import numpy as np


def center2rect(center, height, left, right, angle):

    half_h = height//2

    tl = center + np.array([-left, -half_h])
    tr = center + np.array([+right, -half_h])
    br = center + np.array([+right, +half_h])
    bl = center + np.array([-left, +half_h])

    ct = np.array([tl, tr, br, bl])
    return ct

def find_quadrant(shape, center):
    # todo dont hardcode this
    left = center[0] < (shape[1] / 2)
    top = center[1] > (shape[0] / 2)
    return (left, top)
