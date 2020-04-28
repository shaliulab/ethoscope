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
from ethoscope.roi_builders.helpers import center2rect, find_quadrant, contour_center, rotate_contour, contour_mean_intensity
from scipy.optimize import minimize

class FSLTargetROIBuilder(BaseROIBuilder):

    _adaptive_med_rad = 0.05
    _expected__min_target_dist = 10 # the minimal distance between two targets, in 'target diameter'
    _n_rows = 10
    _n_cols = 2
    _sorted_src_pts = None
    _M = None
    _invM = None
    _dst_points = np.array([(0,-1),
                        (0,0),
                        (-1,0)], dtype=np.float32)


    _description = {"overview": "A flexible ROI builder that allows users to select parameters for the ROI layout."
                               "Lengths are relative to the distance between the two bottom targets (width)",
                    # "arguments": [
                    #                 {"type": "number", "min": 1, "max": 16, "step":1, "name": "n_cols", "description": "The number of columns","default":1},
                    #                 {"type": "number", "min": 1, "max": 16, "step":1, "name": "n_rows", "description": "The number of rows","default":1}
                    #              ]
                    }
                                   
    def __init__(self, n_rows=10, n_cols=21, debug=False, long_side_fraction = 0.26, short_side_fraction = 0.18, mint=100, maxt=255):
        """
        This roi builder uses three black circles drawn on the arena (targets) to align a grid layout:

        IMAGE HERE

        :param n_rows: The number of rows in the grid.
        :type n_rows: int
        :param n_cols: The number of columns.
        :type n_cols: int
        """

        self._n_rows = n_rows
        self._n_cols = n_cols
        self._debug = debug
        self._long_side_fraction = long_side_fraction
        self._short_side_fraction = short_side_fraction
        self._mint = mint
        self._maxt = maxt
        # if self._vertical_fill is None:
        #     self._vertical_fill = self._horizontal_fill
        # if self._right_margin is None:
        #     self._right_margin = self._left_margin
        # if self._bottom_margin is None:
        #     self._bottom_margin = self._top_margin

        super(BaseROIBuilder,self).__init__()

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

        # make median intensity 255
        med = np.median(grey)
        scale = 255/(med)
        cv2.multiply(grey, scale, dst=grey)
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
                    cv2.drawContours(bin, [c], 0, score, -1)

            score_map = cv2.add(bin, score_map)

            # if self._debug or debug:
            #     cv2.imshow("bin_th", cv2.threshold(score_map, 1, 255, cv2.THRESH_BINARY)[1])
            #     cv2.imshow("closing", foreground_model)
            #     cv2.imshow("foreground_model", foreground_model)

            #     cv2.waitKey(0)

        return score_map

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
       
        if debug:
            thresh = cv2.threshold(map, 1, 255, cv2.THRESH_BINARY)[1]
            cv2.imshow("map", thresh)
            cv2.waitKey(0)
        
        bin = np.zeros_like(map)

        # as soon as we have three objects, we stop
        contours = []
        for t in range(0, 255,1):
            cv2.threshold(map, t, 255,cv2.THRESH_BINARY, bin)
            if CV_VERSION == 3:
                _, contours, h = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, h = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            
            if debug:
                cv2.imshow('bin', bin)
                cv2.waitKey(0)

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

        if debug:
            for pt in src_points:
                pt = tuple((int(e) for e in pt))
                thresh = cv2.circle(thresh, pt, 5, 0, -1)

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

    def _split_rois(self, bin, orig):

        bin_orig = bin.copy()

        if CV_VERSION == 3:
            _, contours, _ = cv2.findContours(bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        else:
            contours, _ = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)


        if debug:
            cv2.imshow("bin", bin)
            cv2.waitKey(0)

        while np.count_nonzero(bin) > 0:

            # bin = cv2.morphologyEx(bin, cv2.MORPH_TOPHAT, (9, 9))
            bin = cv2.erode(bin, np.ones((1, 10)))
            if CV_VERSION == 3:
                _, contours, _ = cv2.findContours(bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            else:
                contours, _ = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

            if debug:
                cv2.imshow("eroded_bin", bin)
                cv2.waitKey(0)

            if len(contours) == 20:
                break


        if np.count_nonzero(bin) == 0:
            # TODO Adapt to any number of ROIs
            raise EthoscopeException('I could not find 20 ROIs. Please try again or change the lighting conditions', np.stack((bin_orig, orig), axis=1))

        return contours
   
    def _rois_from_img(self, img):

        grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # rotate the image so ROIs are horizontal        
        rotated, M = self._rotate_img(img)        
        # segment the ROIs out of the rotated image
        bin_rotated = self._segment_rois(rotated, debug=False)[:,:,0]

        center_plot = np.stack((bin_rotated,)*3, axis=2)

        contours = self._split_rois(bin_rotated, grey)
        centers = []
        widths = []
        heights = []
        centers_left = []
        centers_right = []
        angles = []
        rects = []
        for i, ct in enumerate(contours):

            # rect = cv2.boundingRect(ct)
            # x,y,w,h = rect
            ## create a contour from the rect
            ## rect is a list of 4 numbers: x,y on top left corner and width and height of the rectangle
            ## roi is a list of 4 tuples: the x,y coordinates of the 4 squares of the rectangle 
            # roi = np.array([(x,y), (x+w, y), (x+w,y+h), (x, y+h)])
            rect = cv2.minAreaRect(ct)
            xy, wh, angle = rect
            rects.append(rect)
            w = np.max(wh)
            h = np.min(wh)
            roi = cv2.boxPoints(rect).astype(np.int32)

            center = (np.mean([e[0] for e in roi]), np.mean([e[1] for e in roi]))
            center = tuple(int(e) for e in center)
            centers.append(center)
            angles.append(angle)
            roi.reshape((4,1,2))
            cv2.circle(center_plot, center, 10, (0,255,0), -1)
            
            widths.append(w)
            heights.append(h)
            left, _ = find_quadrant(bin_rotated.shape, center)
            if left:
                centers_left.append(center)
            else:
                centers_right.append(center)

        if debug:
            cv2.imshow("center_plot", center_plot)
            cv2.waitKey(0)
        
        median_x_left = np.median([e[0] for e in centers_left])
        median_x_right = np.median([e[0] for e in centers_right])
        
        
        rois = []

        arena_width = self._sorted_src_pts[1,0] - self._sorted_src_pts[2,0]
        arena_height = self._sorted_src_pts[0,1] - self._sorted_src_pts[1,1]

        long_side = int(self._long_side_fraction*arena_width)
        short_side = int(self._short_side_fraction*arena_width)
        # height =  int(0.7*(arena_height*0.8/10))
        height = 0.8*np.median(heights)

        for i, center in enumerate(centers):
            left, _ = find_quadrant(bin_rotated.shape, center)
            angle = angles[i]

            segmented_contour = contours[i]
        
            # corrected_roi = cv2.boxPoints(rects[i])

            if left:
                corrected_roi = center2rect((median_x_left, center[1]), height, left = long_side, right = short_side, angle=angle)
                inner_roi = center2rect((median_x_left, center[1]), height, left = long_side/2, right = short_side/3, angle=angle)
            else:
                corrected_roi = center2rect((median_x_right, center[1]), height, left = short_side, right = long_side, angle=angle)
                inner_roi = center2rect((median_x_right, center[1]), height, left = short_side/3, right = long_side/2, angle=angle)

            center_of_mass = contour_center(corrected_roi)
            
            max_angle = 0.0
            learning_rate = 0.01
            cnt_rot = rotate_contour(corrected_roi, +learning_rate, center_of_mass)
            mean_pos = contour_mean_intensity(grey, cnt_rot)
            cnt_rot = rotate_contour(corrected_roi, -learning_rate, center_of_mass)
            mean_neg = contour_mean_intensity(grey, cnt_rot)
            gradient = np.array([-1,1])[np.argmin(np.array([mean_neg, mean_pos]))]
    
            original_val = contour_mean_intensity(grey, corrected_roi)
            max_val = original_val
            for angle in np.arange(-.25, .25, learning_rate):
            # while not min_found and n_iters < 100:
                inner_cnt_rot = rotate_contour(inner_roi, angle, center_of_mass)
                val = contour_mean_intensity(grey, inner_cnt_rot)
                if val > max_val:
                    max_val = val
                    max_angle = angle

            cnt_rot = rotate_contour(corrected_roi, max_angle, center_of_mass)
            
            # for pixel_moves in np.arange(0,5):
            #     cnt_rot_up = cnt_rot - np.array(0, 1) 
            #     cnt_rot_down = cnt_rot + np.array(0, 1) 
            #     val_up = contour_mean_intensity(grey, cnt_rot_up)
            #     val_down = contour_mean_intensity(grey, cnt_rot_down)
            #     if val_up 


            print(f"ROI_{i+1}")
            print(max_angle)
            print(val)
            print(original_val)

            cv2.drawContours(grey, [inner_roi], -1, (255, 255, 0), 2)
            if max_angle != 0:               
                cv2.drawContours(grey, [inner_cnt_rot], -1, (255, 0, 255), 2)
            

            # fly_roi=cv2.bitwise_and(np.stack((mask,)*img.shape[2], axis=2), img)
            # fly_roi = img[start_row:end_row, start_column:end_column]
            # cv2.imshow(f"ROI_{i}", mask)
            # cv2.waitKey(0)
            
            ####
            # give it the shape expected by programs downstream            
            ct = cnt_rot.reshape((1,4,2)).astype(np.int32)
            # cv2.drawContours(img,[ct], -1, (255,0,0),1,LINE_AA)
            # initialize a ROI object to be returned to the control thread
            # with all the other detected ROIs in the rois list
            rois.append(ROI(ct, idx=i+1))

        if debug:
            cv2.imshow("grey", grey)
            cv2.waitKey(0)

        # if self._debug or debug or True:
        #     for roi in rois:
        #         tl = (roi.rectangle[0], roi.rectangle[1])
        #         br = (roi.rectangle[0] + roi.rectangle[2], roi.rectangle[1] + roi.rectangle[3])
        #         cv2.rectangle(bin_rotated,tl,br, 128, 2)

        #     cv2.imshow("img_rotated", rotated)
        #     cv2.imshow("bin_rotated", bin_rotated)
        #     cv2.imshow("bin_rotated_contours", bin_rotated)
        #     cv2.waitKey(0)
       
        return rotated, M, rois           


    def _rotate_img(self, img):

        bin = self._segment_rois(img)
        # cv2.imshow("segmented_bin",bin)
        # cv2.waitKey(0)
        
        if CV_VERSION == 3:
            _, contours, _ = cv2.findContours(bin[:,:,0], cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        else:
            contours, _ = cv2.findContours(bin[:,:,0], cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

        logging.info(f"Number of contours detected after rotating img: {len(contours)}")  

        angle_sample = []
        for ct in contours:
            rect = cv2.minAreaRect(ct)
            tl, wh, angle = rect
            w = np.max(wh)
            h = np.min(wh)

            # top_inner = tl if tl[0] > arena_roi.shape[1]*0.4 else tl + np.array(w,0)
            # compute the mean of the angles sampled from each rectangle
            # and round to two decimal digits
            angle_sample.append(angle)


        median_angle = np.round(np.median(np.array(angle_sample)), 2)*0.5
        mean_angle = np.round(np.mean(np.array(angle_sample)), 2)
        center = tuple(e/2 for e in img.shape[:2])
        
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        invM = cv2.getRotationMatrix2D(center, -median_angle, 1.0)
        if abs(median_angle) > 10:
            logging.warning("Please ensure correct orientation of the camera")
            logging.warning(f"Angle detected is {median_angle}")
            rotated = img
            return img
        else:
            rotated = cv2.warpAffine(img, M, img.shape[:2][::-1], flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        logging.info(f"Image rotated successfully with angle {median_angle}")
        self._M = M
        self._invM = invM
        self._angle = median_angle
        return rotated, M


    def _get_roi_score_map(self, arena_roi, t, debug=False):

        # reset the score map for this new threshold
        # initialize an array of same shape as input image
        # set to 0 by default and a given pixel to 1 if a ROI overlaps it
        score_map = np.zeros((arena_roi.shape[0], arena_roi.shape[1], 2), dtype=np.uint8)

        # perform binary thresholding
        thresh = cv2.threshold(arena_roi, t, 255, cv2.THRESH_BINARY)[1]

        # morphological operations to denoise
        # kernel used in closing morphological operations
        kernel = (10,10)
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        # morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
        morph = cv2.morphologyEx(morph, cv2.MORPH_CLOSE, kernel)
        # morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
        morph = cv2.morphologyEx(morph, cv2.MORPH_CLOSE, kernel)
        
        # pad with only 1 pixel to avoid segmented regions touching the wall
        padded = cv2.copyMakeBorder(morph, 1, 1, 1, 1, cv2.BORDER_CONSTANT)
        if debug:
            cv2.imshow("padded", padded)
            cv2.moveWindow("padded", 0,800)
    
        edged = cv2.Canny(padded, 50, 100)
        if CV_VERSION == 3:
            _, contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        else:
            contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL,CHAIN_APPROX_SIMPLE)


        half_t = 130


        
        # go through each contour and validate it
        for ct in contours:
            epsilon = 0.001*cv2.arcLength(ct,True)
            approx = cv2.approxPolyDP(ct,epsilon,True)
            rect = cv2.minAreaRect(approx)
            angle = rect[2]
            width = np.max(rect[1])
            height = np.min(rect[1])

            box = cv2.boxPoints(rect).astype(np.int32).reshape((4,1,2))

            # TODO
            # Remove hardcoding
            # Instead, compute these values from the arena dimensions
            # represented by self._sorted_src_pts

            cond1 = (t < half_t and rect[0][1] > arena_roi.shape[0]/2)
            cond2 = (t >= half_t and rect[0][1] < arena_roi.shape[0]/2)
            

            if width > 200 and width < 600 and height > 15 and height < 60:
                if cond1 or cond2:
                    cv2.drawContours(score_map,[box],-1, (255, 0), -1)
            
            else:
                if debug:
                    cv2.drawContours(padded,[box],-1, 255, 10)
                    logging.debug("Did not pass:")
                    logging.debug(width)
                    logging.debug(height)
                    logging.debug(cond1)
                    logging.debug(cond2)
                    cv2.imshow("padded", padded)
                    cv2.waitKey(0)
                
        return score_map


    def _find_arena(self, img):
        # try:
        #     sorted_src_pts = self._find_target_coordinates(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), self._find_blobs)
        # except EthoscopeException:
            # logging.warning("Fall back to find_blobs_new")
        try:
            sorted_src_pts = self._find_target_coordinates(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), self._find_blobs_new)
            self._sorted_src_pts = sorted_src_pts
            wrap_mat = cv2.getAffineTransform(self._dst_points, sorted_src_pts)
            self._wrap_mat = wrap_mat

        except Exception as e:
            logging.warning(e)
            raise e

        
        return sorted_src_pts, wrap_mat
                

    def _segment_rois(self, img, debug=False):

        r"""
        the rois are segmented by:
        * BILFILT
        * THRESH LOOP
           1. MORPH X 5
           2. SURROUND BY BLACK TO AVOID WALL EFFECT
           3. CANNY (edge detection)
           4. FIND CONTS
           5. CONT LOOP
           6. APPROX CONTOUR
           7. MINAREARECT
           8. IF WIDTH AND HEIGHT ARE OK
           9. UPDATE SCORE MAP
        """

        # if self._sorted_src_pts is None
        # the arena is not yet detected
        # then do:
        #  * find the coordinates of the 3 targets in the arena
        #  * compute the affine transformation matrix needed
        #    to transform the three reference points (0,-1), (0,0) and (-1,0)
        #    into the coordinates just found

        if self._sorted_src_pts is None:
            sorted_src_pts, _ = self._find_arena(img)
        # if is not None, the arena was already segmented
        # but we still need to find ROIs inside it
        else:
            if self._M is not None:
                dst = np.append(self._sorted_src_pts, np.zeros((self._sorted_src_pts.shape[0], 1)), axis=1)
                print("dst.shape")
                print(dst.shape)


                sorted_src_pts = np.dot(self._M, dst.T).T
            else:
                sorted_src_pts = self._sorted_src_pts      
            
        arena = np.round(sorted_src_pts.T.reshape((2,3))).astype(np.int32)

        # compute the coordinates of the top left corner
        # based on those of the other three corners
        # assume a trapzeoid
        tl = np.array([-arena[0,1]+arena[0,0]+arena[0,2], -arena[1,1]+arena[1,0]+arena[1,2]]).T.reshape(2,1)
        arena = np.append(arena, tl, axis=1)
        # subset the original image using this ROI and work with it henceforth
        arena_roi= img[arena[1,3]:arena[1,1], arena[0,3]:arena[0,1]]
               
        # store the addition of all the score_map
        # computed on each iteration      
        bin = np.zeros((arena_roi.shape[0], arena_roi.shape[1], 2), dtype=np.uint8)

        blur = cv2.bilateralFilter(arena_roi, 10, 150, 150)
        cv2.destroyAllWindows()
        # cv2.imshow("blur", blur)

        for t in range(self._mint, self._maxt, 5):
            # print(np.unique(bin, return_counts=True))
            score_map = self._get_roi_score_map(blur, t, debug=debug)
            bin = cv2.add(bin, score_map)

            if debug:

                cv2.imshow(f"bin at threshold={t}", bin[:,:,0])
                cv2.moveWindow(f"bin at threshold={t}", 600, 800)
                cv2.waitKey(0)

            
        # bin[bin>=8] = 255
        # bin[bin<=7] = 0
        
        bin = cv2.threshold(bin, 10, 255, cv2.THRESH_BINARY)[1]
        logging.info("ROIs segmented successfully")

        
        # pad bin on all sides so it acquires the same shape as img
        # i.e. it becomes a mask of the ROIs not in the arena
        # but in img
        top = arena[1,3]
        left = arena[0,3]
        bottom = img.shape[0] - arena[1,1]
        right = img.shape[1] - arena[0,1]
        logging.debug(f"Padding binary map with tlbr: {top},{left},{bottom},{right} pixels") 

        bin = cv2.copyMakeBorder(bin, top, bottom, left, right, cv2.BORDER_CONSTANT,0)
     
        assert img.shape[:2] == bin.shape[:2]
        arena = arena.reshape((1,4,2)).astype(np.int32)
        self._arena = arena
        return bin
