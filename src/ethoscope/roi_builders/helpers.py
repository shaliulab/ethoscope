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

def move_contour(cnt, pixels, axis=1):
    if pixels != 0:
        return cnt
    else:
        cnt_moved = [[pt[0] + pixels*(axis==0), pt[1] + pixels*(axis==1)] for pt in cnt]
        return cnt_moved


def refine_contour(cnt, grey):
    max_angle = 0.0
    learning_rate = 0.01
    cnt_rot = rotate_contour(cnt, +learning_rate, center_of_mass)
    mean_pos = contour_mean_intensity(grey, cnt_rot)
    cnt_rot = rotate_contour(cnt, -learning_rate, center_of_mass)
    mean_neg = contour_mean_intensity(grey, cnt_rot)
    gradient = np.array([-1,1])[np.argmin(np.array([mean_neg, mean_pos]))]

    original_val = contour_mean_intensity(grey, cnt)
    max_val = original_val
    for angle in np.arange(-.25, .25, learning_rate):
    # while not min_found and n_iters < 100:
        inner_cnt_rot = rotate_contour(inner_roi, angle, center_of_mass)
        val = contour_mean_intensity(grey, inner_cnt_rot)
        if val > max_val:
            max_val = val
            max_angle = angle

    cnt_rot = rotate_contour(cnt, max_angle, center_of_mass)
    if max_angle != 0:
        cv2.drawContours(grey, [inner_cnt_rot], -1, (255, 0, 255), 2)
        
    cv2.drawContours(grey, [inner_roi], -1, (255, 255, 0), 2)


    print(f"ROI_{i+1}")
    print(max_angle)
    print(val)
    print(original_val)

    original_val = contour_mean_intensity(grey, cnt_rot)
    max_val = original_val
    max_pixel = 0
    for pixel in np.arange(-10, 10, 1):
    # while not min_found and n_iters < 100:
        inner_cnt_moved = move_contour(cnt_rot, pixel)
        val = contour_mean_intensity(grey, inner_cnt_moved)
        if val > max_val:
            max_val = val
            max_pixel = pixel

    final_contour = move_contour(cnt_rot, max_pixel)

    return final_contour, grey, max_angle, max_pixel

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
