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

        cnt_shape = list(cnt.shape)
        coord_slot = cnt_shape.index(2)
        cnt_shape[coord_slot] = 1

        cnt_z = np.append(cnt, np.zeros(tuple(cnt_shape)), axis=coord_slot)
        cnt_rot = np.round(np.dot(M, cnt_z.T).T).astype(np.int32)
        return cnt_rot
    else:
        return cnt

def move_contour(cnt, pixel=0, axis=1):
    if pixel == 0:
        return cnt
    else:
        x = pixel*(axis==0)
        y = pixel*(axis==1)
        # print("x and y")
        # print(x)
        # print(y)
        # print("pixel and axis")
        # print(pixel)
        # print(axis)
        cnt_moved = np.array([[pt[0] + x, pt[1] + y] for pt in cnt])
        return cnt_moved


def refine_contour(cnt, grey, rotate=True, move=True):

    if rotate:
        max_angle = 0.0
        learning_rate = 0.01
        center_of_mass = contour_center(cnt)

        cnt_rot = rotate_contour(cnt, +learning_rate, center_of_mass)
        mean_pos = contour_mean_intensity(grey, cnt_rot)
        cnt_rot = rotate_contour(cnt, -learning_rate, center_of_mass)
        mean_neg = contour_mean_intensity(grey, cnt_rot)
        gradient = np.array([-1,1])[np.argmin(np.array([mean_neg, mean_pos]))]

        original_val = contour_mean_intensity(grey, cnt)
        max_val = original_val
        for angle in np.arange(-.25, .25, learning_rate):

        # while not min_found and n_iters < 100:
            inner_cnt_rot = rotate_contour(cnt, angle, center_of_mass)
            val = contour_mean_intensity(grey, inner_cnt_rot)
            if val > max_val:
                max_val = val
                max_angle = angle

        cnt_rot = rotate_contour(cnt, max_angle, center_of_mass)
        if max_angle != 0:
            cv2.drawContours(grey, [inner_cnt_rot], -1, (255, 0, 255), 2)

        cv2.drawContours(grey, [cnt_rot], -1, (255, 255, 0), 2)

        cnt_rot.reshape((1, *cnt_rot.shape))

    else:
        cnt_rot = cnt
        max_angle = 0


    if move:
        original_val = contour_mean_intensity(grey, cnt_rot)
        max_val = original_val
        max_pixel = 0
        # print("Running moving algorithm for ONE contour")
        for pixel in np.arange(-10, 10, 1):
            inner_cnt_moved = move_contour(cnt=cnt_rot, pixel=pixel, axis=1)
            # import ipdb; ipdb.set_trace()
            val = contour_mean_intensity(grey, inner_cnt_moved)
            # print(pixel)
            # print(val)

            if val > max_val:
                max_val = val
                max_pixel = pixel

        cnt_rot = move_contour(cnt=cnt_rot, pixel=max_pixel)
        # original_val = max_val
        # max_pixel = 0
        # # print("Running moving algorithm for ONE contour")
        # for pixel in np.arange(-100, 100, 10):
        #     inner_cnt_moved = move_contour(cnt=cnt_rot, pixel=pixel,axis=0)
        #     # import ipdb; ipdb.set_trace()
        #     val = contour_mean_intensity(grey, inner_cnt_moved)
        #     # print(pixel)
        #     # print(val)

        #     if val > max_val:
        #         max_val = val
        #         max_pixel = pixel

        final_contour = move_contour(cnt=cnt_rot, pixel=int(max_pixel*0.8),axis=0)




    else:
        final_contour = cnt_rot
        max_pixel = 0

    # if max_pixel != 0:
    #     print("--")
    #     print("Max value")
    #     print(max_val)
    #     print("Original contour")
    #     print(cnt_rot)
    #     print("Moved contour")
    #     print(final_contour)
    #     print("--")

    return final_contour, grey, max_angle, max_pixel

def contour_mean_intensity(grey, cnt):
    """
    A np.array with shape ndotsx2
    """

    grey = cv2.cvtColor(grey, cv2.COLOR_BGR2GRAY)

    mask = np.zeros_like(grey, dtype=np.uint8)
    mask = cv2.drawContours(mask, [cnt], -1, 255, -1)
    mean = cv2.mean(grey, mask=mask)[0]

    return mean

def place_dots(grey, pts, color=255):

    # logging.warning("Placement")
    # logging.warning(pts)
    for pt in pts:
        pt = tuple([int(e) for e in pt])
        cv2.circle(grey, pt, 2, color, -1)
    return grey


def pull_contour_h(cnt, point, side="left"):
    max_dist = -10
    #print("--")
    #print(cnt)
    #print(point)
    sign = -1 if side == "left" else + 1
    funcs = {"left": np.max, "right": np.min}

    distances = np.array([point[0] - corner[0] for corner in cnt])


    #print(distances)
    dist = funcs[side](distances)
    #print(dist)

    diff = int(dist - sign*max_dist)

    #print(diff)
    #print("--")

    cnt = np.array([[corner[0] + diff, corner[1]] for corner in cnt])
    #print(cnt)
    return cnt
