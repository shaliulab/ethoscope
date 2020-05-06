import cv2
import numpy as np
import logging
logging.basicConfig(level=logging.INFO)


def center2rect(center, height, left, right, angle):

    half_h = height//2

    tl = center + np.array([-left, -half_h])
    tr = center + np.array([+right, -half_h])
    br = center + np.array([+right, +half_h])
    bl = center + np.array([-left, +half_h])

    ct = np.array([tl, tr, br, bl], dtype=np.int32)
    return ct

def find_quadrant(shape, center):
    # todo dont hardcode this
    left = center[0] < (shape[1] / 2)
    top = center[1] > (shape[0] / 2)
    return (left, top)

def contour_center(cnt):
    M = cv2.moments(cnt)
    cx = int(M['m10']/M['m00'])
    cy = int(M['m01']/M['m00'])
    return (cx, cy)

def rotate_contour(cnt, angle, center_of_mass=None):
    if angle != 0.0:
        if center_of_mass is None:
            center_of_mass = contour_center(cnt)

        M = cv2.getRotationMatrix2D(center_of_mass, angle, 1.0)
        cnt_z = np.append(cnt, np.zeros((cnt.shape[0], 1)), axis=1)
        cnt_rot = np.round(np.dot(M, cnt_z.T).T).astype(np.int32)
        return cnt_rot
    else:
        return cnt

def contour_mean_intensity(grey, cnt):

    grey = cv2.cvtColor(grey, cv2.COLOR_BGR2GRAY)

    mask = np.zeros_like(grey, dtype=np.uint8)
    mask = cv2.drawContours(mask, [cnt], -1, 255, -1)
    logging.info(grey.shape)
    logging.info(grey.dtype)


    logging.info(mask.shape)
    logging.info(mask.dtype)
    mean = cv2.mean(grey, mask=mask)[0]
    return mean
