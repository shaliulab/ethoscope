__author__ = 'quentin'

import cv2

try:
    CV_VERSION = int(cv2.__version__.split(".")[0])
except:
    CV_VERSION = 2

try:
    from cv2.cv import CV_CHAIN_APPROX_SIMPLE as CHAIN_APPROX_SIMPLE
    from cv2.cv import CV_AA as LINE_AA
except ImportError:
    from cv2 import CHAIN_APPROX_SIMPLE
    from cv2 import LINE_AA

import numpy as np
import logging
debug=False
# level = CFG.content["logging"]["level"]
level = logging.DEBUG
logging.basicConfig(level=level)
from ethoscope.roi_builders.roi_builders import BaseROIBuilder
from ethoscope.core.roi import ROI
from ethoscope.utils.debug import EthoscopeException
import itertools


class TargetGridROIBuilder(BaseROIBuilder):

    _adaptive_med_rad = 0.05
    _expected__min_target_dist = 10 # the minimal distance between two targets, in 'target diameter'
    _n_rows = 10
    _n_cols = 2
    _top_margin =  0
    _bottom_margin = None
    _left_margin = 0
    _right_margin = None
    _horizontal_fill = 1
    _vertical_fill = None

    _wrap_mat = None
    _sorted_src_pts = None
    _dst_points = None
    _M = None
    _invM = None
    _angle = None


    _description = {"overview": "A flexible ROI builder that allows users to select parameters for the ROI layout."
                               "Lengths are relative to the distance between the two bottom targets (width)",
                    "arguments": [
                                    {"type": "number", "min": 1, "max": 16, "step":1, "name": "n_cols", "description": "The number of columns","default":1},
                                    {"type": "number", "min": 1, "max": 16, "step":1, "name": "n_rows", "description": "The number of rows","default":1},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "top_margin", "description": "The vertical distance between the middle of the top ROIs and the middle of the top target.","default":0.0},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "bottom_margin", "description": "Same as top_margin, but for the bottom.","default":0.0},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "right_margin", "description": "Same as top_margin, but for the right.","default":0.0},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "left_margin", "description": "Same as top_margin, but for the left.","default":0.0},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "horizontal_fill", "description": "The proportion of the grid space used by the roi, horizontally.","default":0.90},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "vertical_fill", "description": "Same as horizontal_margin, but vertically.","default":0.90},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "horizontal_pad", "description": "The proportion of the grid that ROIs are displaced from the center, horizontally.","default":0.0},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "vertical_pad", "description": "Same as horizontal_pad, but vertically.","default":0.0}
                                   ]}
                                   
    def __init__(self, n_rows=1, n_cols=1, top_margin=0, bottom_margin=0,
                 left_margin=0, right_margin=0, horizontal_fill=.9, vertical_fill=.9,
                 horizontal_pad = 0.0, vertical_pad = 0.0,
                 horizontal_offset = 0.0, vertical_offset = 0.0, direction=1, debug=False
                 ):
        """
        This roi builder uses three black circles drawn on the arena (targets) to align a grid layout:

        IMAGE HERE

        :param n_rows: The number of rows in the grid.
        :type n_rows: int
        :param n_cols: The number of columns.
        :type n_cols: int
        :param top_margin: The vertical distance between the middle of the top ROIs and the middle of the top target
        :type top_margin: float
        :param bottom_margin: same as top_margin, but for the bottom.
        :type bottom_margin: float
        :param left_margin: same as top_margin, but for the left side.
        :type left_margin: float
        :param right_margin: same as top_margin, but for the right side.
        :type right_margin: float
        :param horizontal_fill: The proportion of the grid space user by the roi, horizontally (between 0 and 1).
        :type horizontal_fill: float
        :param vertical_fill: same as vertical_fill, but horizontally.
        :type vertical_fill: float
        """

        self._n_rows = n_rows
        self._n_cols = n_cols
        self._top_margin =  top_margin
        self._bottom_margin = bottom_margin
        self._left_margin = left_margin
        self._right_margin = right_margin
        self._horizontal_fill = horizontal_fill
        self._vertical_fill = vertical_fill
        self._horizontal_pad = horizontal_pad
        self._vertical_pad = vertical_pad
        self._horizontal_offset = horizontal_offset
        self._vertical_offset = vertical_offset
        self._direction = direction
        self._debug = debug

        # if self._vertical_fill is None:
        #     self._vertical_fill = self._horizontal_fill
        # if self._right_margin is None:
        #     self._right_margin = self._left_margin
        # if self._bottom_margin is None:
        #     self._bottom_margin = self._top_margin

        super(TargetGridROIBuilder,self).__init__()

    def _find_blobs(self, img, scoring_fun=None):

        grey = img

        if scoring_fun is None:
            scoring_fun = self._score_targets

        rad = int(self._adaptive_med_rad * grey.shape[1])
        if rad % 2 == 0:
            rad += 1

        med = np.median(grey)
        scale = 255/(med)
        cv2.multiply(grey, scale, dst=grey)
        bin = np.copy(grey)
        thresh = np.copy(grey)
        score_map = np.zeros_like(bin)
        grey_orig = grey.copy()

        for t in range(0, 255, 5):
            cv2.threshold(grey_orig, t, 255, cv2.THRESH_BINARY_INV, thresh)
            if np.count_nonzero(thresh) > 0.7 * grey.shape[0] * grey.shape[1]:
                continue
            if CV_VERSION == 3:
                _, contours, h = cv2.findContours(thresh, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, h = cv2.findContours(thresh, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

            bin.fill(0)
            for c in contours:
                score = scoring_fun(c, grey)
                if score > 0:
                    cv2.drawContours(bin, [c], 0, score, -1)

                # cv2.drawContours(grey, [c], -1, 255, 2)

            # cv2.imshow("grey", grey)im
            # cv2.waitKey(0)

            cv2.add(bin, score_map, score_map)

        return score_map


    def _find_blobs_new(self, img, scoring_fun=None):

        grey = img
        if scoring_fun is None:
            scoring_fun = self._score_circles

        # radius of dots is 0.1 * width of image
        # units?
        rad = int(self._adaptive_med_rad * grey.shape[1])
        # make sure it is an odd
        if rad % 2 == 0:
            rad += 1

        logging.warning(f"Radius: {rad}")

        # make median intensity 255
        med = np.median(grey)
        scale = 255/(med)
        cv2.multiply(grey, scale, dst=grey)
        logging.warning(np.median(grey))       
        bin = np.copy(grey)
        score_map = np.zeros_like(bin)
        grey_orig = grey.copy()

        for threshold in range(0, 255, 5):
            cv2.threshold(grey, threshold, 255, cv2.THRESH_BINARY_INV, bin)
            non_zero_pixels = np.count_nonzero(bin)
            # if this threshold operation leaves
            # more than 70% white pixels, continue
            # until loop is over           
            if non_zero_pixels > 0.7 * grey.shape[0] * grey.shape[1]:
                continue

            if CV_VERSION == 3:
                _, contours, h = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, h = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

            foreground_model = cv2.drawContours(grey.copy(), contours, -1, 255, -1)
            _, foreground_model = cv2.threshold(foreground_model, 254, 255, cv2.THRESH_BINARY)
            for i in range(10):
                foreground_model = cv2.morphologyEx(foreground_model, cv2.MORPH_CLOSE, (5, 5))


            if CV_VERSION == 3:
                _, contours, h = cv2.findContours(foreground_model, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, h = cv2.findContours(foreground_model, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)


            bin.fill(0)

            for c in contours:
                score = scoring_fun(c)
                if score > 0:
                    if (self._debug or debug):
                        detected_contours = cv2.drawContours(grey.copy(), [c], -1, 255 -1)
                        cv2.imshow("detected_contours", detected_contours)

                    cv2.drawContours(bin, [c], 0, score, -1)

            score_map = cv2.add(bin, score_map)

            if self._debug or debug:
                cv2.imshow("bin_th", cv2.threshold(score_map, 1, 255, cv2.THRESH_BINARY)[1])
                cv2.imshow("closing", foreground_model)
                cv2.imshow("foreground_model", foreground_model)

                cv2.waitKey(0)

        return score_map

    @staticmethod
    def _adjust(centres, n_col, n_row, pad, offset, direction=1, axis=0):

        if len(centres) != (n_col * n_row):
            raise ValueError("Number of centres should be equal to n_col * n_row")


        # sort the centers based on the value in the axis position
        # i.e. if axis is 0, sort by the 0th value, which corresponds to the x dimension
        # this results on a list with all centers in the first column, then the second, and so on
        # i.e. if axis is 1, sort by the 1st value, which corresponds to the y dimension
        # this results on a list with all centers in the first row, then the second, and so on
        all_centres_sorted = sorted(centres, key=lambda x: x[axis])
        index = -1
        sign = -1
        shape = [n_row, n_col]

        for i, centre in enumerate(all_centres_sorted):

            if i % shape[axis] == 0:
                index += 1

            if index == shape[1-axis] // 2 and shape[1-axis] % 2 != 0:
                continue

            if index >= shape[1-axis] // 2:
                sign = 1

            offset_multiplier = -index + shape[1-axis] if direction == -1 else index

            shift = np.array([sign * pad + direction* offset_multiplier * offset,] * 2)
            #shift = np.array([sign * pad + index * offset,] * 2)

            shift[1-axis] = 0

            all_centres_sorted[i] = all_centres_sorted[i] + shift

        return all_centres_sorted

    def _make_grid(self, n_col, n_row,
              top_margin=0.0, bottom_margin=0.0,
              left_margin=0.0, right_margin=0.0,
              horizontal_fill=1.0, vertical_fill=1.0,
              horizontal_pad=0.0, vertical_pad=0.0,
              horizontal_offset=0.0, vertical_offset=0.0):

        y_positions = (np.arange(n_row) * 2.0 + 1) * (1-top_margin-bottom_margin)/(2*n_row) + top_margin
        x_positions = (np.arange(n_col) * 2.0 + 1) * (1-left_margin-right_margin)/(2*n_col) + left_margin
        all_centres = [np.array([x, y]) for x, y in itertools.product(x_positions, y_positions)]

        # first adjust the axis 1 and then axiss 0
        # as the program expects the ROIs to be sorted
        # according to the value in 0th axis (X)
        # i.e. column by column
        all_centres = self._adjust(all_centres, n_col, n_row, vertical_pad, vertical_offset, direction=self._direction, axis=1)
        all_centres = self._adjust(all_centres, n_col, n_row, horizontal_pad, horizontal_offset, axis=0)


        grid_shape = (n_row*50, n_col*50)
        print(grid_shape)
        grid = np.zeros(grid_shape, dtype=np.uint8)
        for c in all_centres:
            print(c)
            grid = cv2.circle(grid, tuple([int(c[0]*grid_shape[1]), int(c[1]*grid_shape[0])]), 2, 255, -1)

        if self._debug:
            cv2.imshow("grid", grid)
            cv2.waitKey(0)

        sign_mat = np.array([
            [-1, -1],
            [+1, -1],
            [+1, +1],
            [-1, +1]
        ])

        xy_size_vec = np.array([horizontal_fill/float(n_col), vertical_fill/float(n_row)]) / 2.0
        rectangles = [sign_mat *xy_size_vec + c for c in all_centres]
        return rectangles


    def _points_distance(self, pt1, pt2):
        x1 , y1  = pt1
        x2 , y2  = pt2
        return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def _score_circles(self, contour):

        area = cv2.contourArea(contour)

        if area < 400 or area > 800:
            return 0

        ((x, y), radius) = cv2.minEnclosingCircle(contour)
        # if area was zero the functionw would have already returned                
        ratio = np.pi*radius**2 / area
        # print(ratio)
       
        if ratio > 1 and ratio < 1.5:
            return 1
        else:
            return 0

    def _score_targets(self,contour, im):

        area = cv2.contourArea(contour)
        perim = cv2.arcLength(contour,True)

        if perim == 0:
            return 0
        circul =  4 * np.pi * area / perim ** 2

        if circul < .8: # fixme magic number
            return 0
        return 1

    def _find_target_coordinates(self, img, blob_function):
        
        map = blob_function(img)
        
        if self._debug or True:
            thresh = cv2.threshold(map, 1, 255, cv2.THRESH_BINARY)[1]
            cv2.imshow("map", thresh)
            cv2.waitKey(0)
        
        bin = np.zeros_like(map)

        # as soon as we have three objects, we stop
        contours = []
        for t in range(0, 255,1):
            cv2.threshold(map, t, 255,cv2.THRESH_BINARY  ,bin)
            if CV_VERSION == 3:
                _, contours, h = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, h = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)


            if len(contours) <3:
                raise EthoscopeException("There should be three targets. Only %i objects have been found" % (len(contours)), img)
            if len(contours) == 3:
                break

        target_diams = [cv2.boundingRect(c)[2] for c in contours]

        mean_diam = np.mean(target_diams)
        mean_sd = np.std(target_diams)

        if mean_sd/mean_diam > 0.10:
            raise EthoscopeException("Too much variation in the diameter of the targets. Something must be wrong since all target should have the same size", img)

        src_points = []
        for c in contours:
            moms = cv2.moments(c)
            x, y = moms["m10"]/moms["m00"],  moms["m01"]/moms["m00"]
            src_points.append((x, y))

        a, b, c = src_points

        if self._debug:
            for pt in src_points:
                pt = tuple((int(e) for e in pt))
                thresh = cv2.circle(thresh, pt, 5, 0, -1)

            cv2.imshow("blobs", thresh)
            cv2.waitKey(0)

        pairs = [(a,b), (b,c), (a,c)]

        dists = [self._points_distance(*p) for p in pairs]
        # that is the AC pair
        hypo_vertices = pairs[np.argmax(dists)]

        # this is B : the only point not in (a,c)
        for sp in src_points:
            if not sp in hypo_vertices:
                break
        sorted_b = sp

        dist = 0
        for sp in src_points:
            if sorted_b is sp:
                continue
            # b-c is the largest distance, so we can infer what point is c
            if self._points_distance(sp, sorted_b) > dist:
                dist = self._points_distance(sp, sorted_b)
                sorted_c = sp

        # the remaining point is a
        sorted_a = [sp for sp in src_points if not sp is sorted_b and not sp is sorted_c][0]
        sorted_src_pts = np.array([sorted_a, sorted_b, sorted_c], dtype=np.float32)
        return sorted_src_pts

    def _rois_from_img(self, img):

        sorted_src_pts = self._find_target_coordinates(img)
        dst_points = np.array([(0,-1),
                               (0,0),
                               (-1,0)], dtype=np.float32)
        wrap_mat = cv2.getAffineTransform(dst_points, sorted_src_pts)

        rectangles = self._make_grid(self._n_cols, self._n_rows,
                                     self._top_margin, self._bottom_margin,
                                     self._left_margin,self._right_margin,
                                     self._horizontal_fill, self._vertical_fill)

        shift = np.dot(wrap_mat, [1,1,0]) - sorted_src_pts[1] # point 1 is the ref, at 0,0
        rois = []
        for i,r in enumerate(rectangles):
            r = np.append(r, np.zeros((4,1)), axis=1)
            mapped_rectangle = np.dot(wrap_mat, r.T).T
            mapped_rectangle -= shift
            ct = mapped_rectangle.reshape((1,4,2)).astype(np.int32)
            cv2.drawContours(img,[ct], -1, (255,0,0),1,LINE_AA)
            rois.append(ROI(ct, idx=i+1))

            # cv2.imshow("dbg",img)
            # cv2.waitKey(0)
        return rois


    def _rois_from_img_new(self, img):
        
        rotated = self._rotate_img(img)
        cv2.imshow("img_rotated", rotated)
        cv2.waitKey(0)
        
        bin_rotated = self._segment_rois(rotated)

        if CV_VERSION == 3:
            _, contours, _ = cv2.findContours(bin_rotated, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        else:
            contours, _ = cv2.findContours(bin_rotated, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
        

        print(f"Detected {len(contours)} contours")
        rois = []
        for i, ct in enumerate(contours):
            rect = cv2.boundingRect(ct)
            print(rect)
            x,y,w,h = rect
            tl = (x,y)
            cv2.rectangle(bin_rotated,(x,y),(x+w,y+h), 128, 2)

            roi = np.array([(x,y), (x+w, y), (x+w,y+h), (x, y+h)])
            # roi = np.dot(np.linalg.inv(self._M), np.append(roi, np.zeros((roi.shape[0], 1)), axis=1).T).T
            # roi = np.dot(self._invM, np.append(roi, np.zeros((roi.shape[0], 1)), axis=1).T).T

            # top_inner = tl if tl[0] > arena_roi.shape[1]*0.4 else tl + np.array(w,0)
            # compute the mean of the angles sampled from each rectangle
            # and round to two decimal digits
            ct = roi.reshape((1,4,2)).astype(np.int32)
            cv2.drawContours(img,[ct], -1, (255,0,0),1,LINE_AA)
            rois.append(ROI(ct, idx=i+1))


        cv2.imshow("img_rotated", rotated)
        cv2.imshow("bin_rotated", bin_rotated)
        cv2.imshow("bin_rotated_contours", bin_rotated)
        cv2.waitKey(0)
        return rotated, rois            


    def _rotate_img(self, img):

        bin = self._segment_rois(img)
        cv2.imshow("segmented_bin",bin)
        cv2.waitKey(0)
        
        if CV_VERSION == 3:
            _, contours, _ = cv2.findContours(bin, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        else:
            contours, _ = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
        

        angle_sample = []
        for ct in contours:
            rect = cv2.minAreaRect(ct)
            tl, wh, angle = rect
            w, h = wh
            # top_inner = tl if tl[0] > arena_roi.shape[1]*0.4 else tl + np.array(w,0)
            # compute the mean of the angles sampled from each rectangle
            # and round to two decimal digits
            angle_sample.append(angle)


        median_angle = np.round(np.median(np.array(angle_sample)), 2)
        mean_angle = np.round(np.mean(np.array(angle_sample)), 2)
        center = tuple(e/2 for e in img.shape[:2]) 
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        invM = cv2.getRotationMatrix2D(center, -median_angle, 1.0)
        if abs(median_angle) > 10:
            logging.warning("Please ensure correct orientation of the camera")
            rotated = img
            return img
        else:
            rotated = cv2.warpAffine(img, M, img.shape[:2][::-1], flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        logging.warning(f"Image rotated successfully with angle {median_angle}")
        self._M = M
        self._invM = invM
        self._angle = median_angle
        return rotated


    def _segment_rois(self, img):

        if self._sorted_src_pts is None:
            try:
                sorted_src_pts = self._find_target_coordinates(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), self._find_blobs)
            except EthoscopeException:
                logging.warning("Fall back to find_blobs_new")
                sorted_src_pts = self._find_target_coordinates(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), self._find_blobs_new)
            finally:
                self._sorted_src_pts = sorted_src_pts
                dst_points = np.array([
                    (0,-1),
                    (0,0),
                    (-1,0)
                ], dtype=np.float32)
        
                wrap_mat = cv2.getAffineTransform(dst_points, sorted_src_pts)
                self._wrap_mat = wrap_mat
                self._dst_points = dst_points

        else:
            dst_points = self._dst_points
            wrap_mat = self._wrap_mat
            M = self._M
            if M is not None:
                sorted_src_pts = np.dot(M, np.append(self._sorted_src_pts, np.zeros((self._sorted_src_pts.shape[0], 1)), axis=1).T).T
            else:
                sorted_src_pts = self._sorted_src_pts


            
        if self._debug:
            coords = img.copy()
            for pt in sorted_src_pts:
                print(pt)
                coords = cv2.circle(coords, tuple([int(e) for e in pt]), 25, 255, -1)
        
            cv2.imshow("coords",coords)
            cv2.waitKey(0)


       

        ## ---- NEW
        dst_points_no_shift = np.append(dst_points+1, np.zeros((3,1)), axis=1)
        # dimensions x (points + 1)
        # the last column is all zeros so the last row of the afine transformation is ignored

        arena = (np.dot(wrap_mat, dst_points_no_shift.T))
        shift = arena[:,1] - sorted_src_pts[1] # point 1 is the ref, at 0,0
        #shift = np.dot(wrap_mat, [1,1,0]) - sorted_src_pts[1] # point 1 is the ref, at 0,0
        shift_rep = np.repeat(shift, 3).reshape((2,3))
        arena -= shift_rep

        # assuming it was a rectangle
        # tl = np.array([arena[0,2], arena[1,0]]).T.reshape(2,1)
        # it actually is a trapezoid because there is some shear due to:
        # * a non horizontal camera
        # * non perpendicular walls
        tl = np.array([-arena[0,1]+arena[0,0]+arena[0,2], -arena[1,1]+arena[1,0]+arena[1,2]]).T.reshape(2,1)
     
        arena = np.append(arena, tl, axis=1)
        arena_int = arena.astype(np.int16)

        #start_row:end_row, start_column:end_column
        arena_roi= img[arena_int[1,3]:arena_int[1,1], arena_int[0,3]:arena_int[0,1]]
        # print(arena_roi.dtype)

        # start = (np.array(myroi.shape) // 3)[:2][::-1]
        # end = (2 * np.array(myroi.shape) // 3)[:2][::-1]
        kernel = (10,10)
                
        #blur = cv2.blur(arena_roi, kernel)
        blur = cv2.bilateralFilter(arena_roi, 10, 150, 150)

        bin = np.zeros((arena_roi.shape))

        for t in range(120, 181, 5):
            thresh = cv2.threshold(blur, t, 255, cv2.THRESH_BINARY)[1]
        
        # thresh1 = cv2.threshold(blur[0:4*blur.shape[0]//10,:], 160, 255, cv2.THRESH_BINARY)[1]
        # thresh2 = cv2.threshold(blur[4*blur.shape[0]//10:5*blur.shape[0]//10,:], 140, 255, cv2.THRESH_BINARY)[1]
        # thresh3 = cv2.threshold(blur[5*blur.shape[0]//10:10*blur.shape[0]//10,:], 120, 255, cv2.THRESH_BINARY)[1]
        # thresh = np.append(thresh1, thresh2, axis=0)
        # thresh = np.append(thresh, thresh3, axis=0)

            # cv2.imshow("bil_filter", blur)
            # cv2.imshow("thresh", thresh)       
            # cv2.waitKey(0)
            
            closing = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            closing = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            closing = cv2.morphologyEx(closing, cv2.MORPH_CLOSE, kernel)

            padded = cv2.copyMakeBorder(closing, 1, 1, 1, 1, cv2.BORDER_CONSTANT)
        
            edged = cv2.Canny(padded, 50, 100)
            if CV_VERSION == 3:
                _, contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            else:
                contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL,CHAIN_APPROX_SIMPLE)
            
            # print(len(contours))
            # print(sorted([cv2.contourArea(ct) for ct in contours])[::-1])
            # contours = sorted(contours, reverse=True, key=lambda x: cv2.minAreaRect(x))

            # cv2.imshow("closing", padded)
            # cv2.moveWindow("closing",2000,800)
            # cv2.imshow("edged", edged)
            # cv2.moveWindow("edged",2000,400)
            
            score_map = np.zeros((arena_roi.shape))


            for ct in contours:
                epsilon = 0.001*cv2.arcLength(ct,True)
                approx = cv2.approxPolyDP(ct,epsilon,True)
                rect = cv2.minAreaRect(approx)
                angle = rect[2]
                width = rect[1][0]
                height = rect[1][1]
                   
                box = cv2.boxPoints(rect)
                box = np.int0(box)
                if width > 200 and width < 600 and height > 15 and height < 60:
                    if (t < 150 and rect[1][0] > arena_roi.shape[0]/2) or (t > 150 and rect[1][0] < arena_roi.shape[0]/2):
                        # print("Shape of a contour")
                        # print(box.shape)
                        # print(box)

                        

                        cv2.drawContours(score_map,[box],0,(255,255,255),-1)
                        bin = cv2.add(bin, score_map)


                # cv2.drawContours(arena_roi, [ct], -1, (0,255,0), -1)

                # print("angle")
                # print(angle)
                # print(f"Size: {width}x{height}")

            # cv2.imshow("arena_roi", arena_roi)
            # cv2.moveWindow("arena_roi",2000,200)
            # cv2.waitKey(0)

        bin = cv2.threshold(bin, 8, 255, cv2.THRESH_BINARY)[1]
        bin = cv2.convertScaleAbs(bin)
        bin = cv2.cvtColor(bin, cv2.COLOR_BGR2GRAY)
        # bin = bin.astype(np.uint8)
        logging.warning("ROIs segmented successfully")
        # print(img.shape)
        # print(bin.shape)
        

        #start_row:end_row, start_column:end_column
        #arena_roi= img[arena_int[1,3]:arena_int[1,1], arena_int[0,3]:arena_int[0,1]]

        top = arena_int[1,3]
        left = arena_int[0,3]
        bottom = img.shape[0] - arena_int[1,1]
        right = img.shape[1] - arena_int[0,1]
        print(f"{top},{left},{bottom},{right} ") 
        try:
            bin = cv2.copyMakeBorder(bin, top, bottom, left, right, cv2.BORDER_CONSTANT,0)
        except Exception:
            import ipdb; ipdb.set_trace()
        # print(bin.shape)
        assert img.shape[:2] == bin.shape
        print("Look here")
        print(arena.dtype)
        print(arena.dtype)
        arena = arena.reshape((1,4,2)).astype(np.int16)
        self._arena = arena
        return bin
        
        

        # cv2.imshow("rotated", rotated)
        # cv2.moveWindow("rotated", 2000, 600)
        # cv2.imshow("original", img)
        # cv2.moveWindow("original", 2000, 100)
        # cv2.waitKey(0)
        
        # ## ----

        # identity = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
        # # identity = np.array([[np.random.uniform(0,2000,1)]*4,]*4).reshape((4,4))
        # print(identity)
        # print(identity.shape)
        
        
        # TODO
        #
        # Put this in _rois_from_img and comment it to make it more legible
        # rois = []
        # for i,r in enumerate(rectangles):
        #     r = np.append(r, np.zeros((4,1)), axis=1)
        #     mapped_rectangle = np.dot(wrap_mat, r.T).T
        #     # mapped rectangle must be 4x2            
        #     mapped_rectangle = np.dot(identity, mapped_rectangle)
            
        #     mapped_rectangle -= shift
        #     ct = mapped_rectangle.reshape((1,4,2)).astype(np.int32)
        #     cv2.drawContours(img,[ct], -1, (255,0,0),1,LINE_AA)
        #     rois.append(ROI(ct, idx=i+1))

        #     if self._debug:
        #         cv2.imshow("thresh", thresh)
        #         cv2.imshow("edged", edged)
        #         cv2.imshow("dbg",img)
        #         cv2.waitKey(0)

        # reshape the arena onject so it has the expected shape
        # it should be
        # 1 x ncols x nrows       
        # new_shape = (1,arena.shape[1],arena.shape[0])
        # arena = arena.T.reshape(new_shape).astype(np.int)

        # return rois, arena


class ThirtyFliesMonitorWithTargetROIBuilder(TargetGridROIBuilder):

    _description = {"overview": "The default sleep monitor arena with ten rows of two tubes.",
                    "arguments": []}

    def __init__(self):
        r"""
        Class to build ROIs for a two-columns, ten-rows for the sleep monitor
        (`see here <https://github.com/gilestrolab/ethoscope_hardware/tree/master/arenas/arena_10x2_shortTubes>`_).
        """
        #`sleep monitor tube holder arena <todo>`_

        super(SleepMonitorWithTargetROIBuilder, self).__init__(n_rows=10,
                                                               n_cols=3,
                                                               top_margin= 6.99 / 111.00,
                                                               bottom_margin = 6.99 / 111.00,
                                                               left_margin = -.033,
                                                               right_margin = -.033,
                                                               horizontal_fill = .975,
                                                               vertical_fill= .7
                                                               )

class FSLSleepMonitorWithTargetROIBuilder(TargetGridROIBuilder):
    
    _description = {"overview": "The default sleep monitor arena with ten rows of two tubes. ROIs adapted to FSL lab.",
                    "arguments": []}

    def __init__(self):
        r"""
        Class to build ROIs for a two-columns, ten-rows for the sleep monitor
        (`see here <https://github.com/gilestrolab/ethoscope_hardware/tree/master/arenas/arena_10x2_shortTubes>`_).
        """
        #`sleep monitor tube holder arena <todo>`_

        super(FSLSleepMonitorWithTargetROIBuilder, self).__init__(n_rows=10,
                                                               n_cols=2,
                                                               top_margin= 6.99 / 111.00,
                                                               bottom_margin = 6.99 / 111.00,
                                                               left_margin = 0,
                                                               right_margin = 0,
                                                               horizontal_fill = .8,
                                                               vertical_fill= .65,
                                                            #    horizontal_pad = 0,
                                                               horizontal_pad = .05,
                                                               vertical_pad = 0,
                                                               vertical_offset = 0,
                                                            #    vertical_offset = 0.002,
                                                               direction=-1
                                                               )

class SleepMonitorWithTargetROIBuilder(TargetGridROIBuilder):

    _description = {"overview": "The default sleep monitor arena with ten rows of two tubes.",
                    "arguments": []}

    def __init__(self):
        r"""
        Class to build ROIs for a two-columns, ten-rows for the sleep monitor
        (`see here <https://github.com/gilestrolab/ethoscope_hardware/tree/master/arenas/arena_10x2_shortTubes>`_).
        """
        #`sleep monitor tube holder arena <todo>`_

        super(SleepMonitorWithTargetROIBuilder, self).__init__(n_rows=10,
                                                               n_cols=2,
                                                               top_margin= 6.99 / 111.00,
                                                               bottom_margin = 6.99 / 111.00,
                                                               left_margin = -.033,
                                                               right_margin = -.033,
                                                               horizontal_fill = .975,
                                                               vertical_fill= .7
                                                               )



class OlfactionAssayROIBuilder(TargetGridROIBuilder):
    _description = {"overview": "The default odor assay roi layout with ten rows of single tubes.",
                    "arguments": []}
    def __init__(self):
        """
        Class to build ROIs for a one-column, ten-rows
        (`see here <https://github.com/gilestrolab/ethoscope_hardware/tree/master/arenas/arena_10x1_longTubes>`_)
        """
        #`olfactory response arena <todo>`_

        super(OlfactionAssayROIBuilder, self).__init__(n_rows=10,
                                                               n_cols=1,
                                                               top_margin=6.99 / 111.00,
                                                               bottom_margin =6.99 / 111.00,
                                                               left_margin = -.033,
                                                               right_margin = -.033,
                                                               horizontal_fill = .975,
                                                               vertical_fill= .7
                                                               )

class ElectricShockAssayROIBuilder(TargetGridROIBuilder):
    _description = {"overview": "A ROI layout for the automatic electric shock. 5 rows, 1 column",
                    "arguments": []}
    def __init__(self):
        """
        Class to build ROIs for a one-column, five-rows
        (`Add gitbook URL when ready`_)
        """
        #`olfactory response arena <todo>`_

        super(ElectricShockAssayROIBuilder, self).__init__(n_rows=5,
                                                               n_cols=1,
                                                               top_margin=0.1,
                                                               bottom_margin =0.1,
                                                               left_margin = -.065,
                                                               right_margin = -.065,
                                                               horizontal_fill = .975,
                                                               vertical_fill= .7
                                                               )


class HD12TubesRoiBuilder(TargetGridROIBuilder):
    _description = {"overview": "The default high resolution, 12 tubes (1 row) roi layout",
                    "arguments": []}


    def __init__(self):
        r"""
        Class to build ROIs for a twelve columns, one row for the HD tracking arena
        (`see here <https://github.com/gilestrolab/ethoscope_hardware/tree/master/arenas/arena_mini_12_tubes>`_)
        """


        super(HD12TubesRoiBuilder, self).__init__( n_rows=1,
                                                   n_cols=12,
                                                   top_margin= 1.5,
                                                   bottom_margin= 1.5,
                                                   left_margin=0.05,
                                                   right_margin=0.05,
                                                   horizontal_fill=.7,
                                                   vertical_fill=1.4
                                                   )
