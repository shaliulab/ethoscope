__author__ = 'antonio'

import logging

import cv2
import numpy as np

import os
import os.path
home_folder = os.environ["HOME"]

from ethoscope.core.variables import CoreMovement, PeripheryMovement, BodyMovement
from ethoscope.trackers.adaptive_bg_tracker import AdaptiveBGModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RichAdaptiveBGModel(AdaptiveBGModel):
    """
    Extract extra behavioral features inspired by
    https://elifesciences.org/articles/34497
    These features are:
      (1) periphery movement (PM), which characterizes movements of the legs, head and wings.
      (2) core movement (CM), which quantifies movements of the thorax and abdomen.
      (3) centroid displacement (CD), which quantifies whole body displacement.

      (3) Is implemented in the AdaptiveBGModel class as the XYDistance instance,
      however (1) and (2) are not and could potentially be very useful to distinguish
      micromovements like grooming. See figure 1.E from https://science.sciencemag.org/content/367/6476/440
      for a similar implementation of the same ideas.

      Distinguishing between stillness and micromovements holds the potential power to
      better estimate sleep by not overestimating it,
      thus leading to more accurate behavioral monitoring and thus
      a more accurate representation of the biological phenomena.
    """

    _body_parts = ("body")
    _description = {
        "overview": "An extended tracker for fruit flies. One animal per ROI.",
        "arguments": [
            {"type": "str", "value": "FALSE", "name": "debug", "description": "If True, I will save to /tmp all the computed foregrounds with format foreground_ROI_DD_t_MS.png"},
            {"type": "number", "value": 1, "name": "scale_factor", "description": """
            If less than 1, the resolution of the images is decreased accordingly (for computational efficiency) in the fly segmentation step.
            However, the pixel difference part stays with original resolution
            """
            },
            
        ]
    }

    # minimum foreground intensity that is considered to compute
    # the body parts of the fly
    # note that besides being greater than this value,
    # they need to be included in the ellipse mask
    # 0 means all pixels are taken into account
    # (and then masked so only a fraction actually does)
    _minimum_change = 20


    def __init__(self, *args, scale_factor=1, **kwargs):
        super().__init__(*args, **kwargs)
        self._fly_pixel_count = None
        self._last_movements = {part: None for part in self._body_parts}
        self._null_dist = None
        self.old_image = None
        self.old_datapoints = None
        self._old_ellipse = None
        self._SCALE_FACTOR=scale_factor
        #self._debug = True

    # def _get_coordinates_of_parts(self, foreground):
    #     """
    #     Compute coordinates of the core and the periphery of the fly.
    #     The coordinates of each part are represented with a list of tuples
    #     where each tuple contains the x and y coordinate of one pixel.
    #     """

    #     non_zero_index = np.where(foreground > 0)

    #     self._fly_pixel_count = len(non_zero_index)

    #     median = np.median(non_zero_index)

    #     core = list(zip(*np.where(foreground < median)))
    #     periphery = list(zip(*np.where(foreground > median)))

    #     coordinates = {"core": core, "periphery": periphery}
    #     return coordinates

    @property
    def old_ellipse(self):
        if self._old_ellipse.tolist() is None:
            ellipse = np.zeros(self._roi.rectangle[2:4][::-1], dtype=np.uint8)
        else:
            ellipse = self._old_ellipse

        return ellipse

    @old_ellipse.setter
    def old_ellipse(self, ellipse):
        self._old_ellipse = ellipse

    # def _get_body(self, foreground, ellipse):
    #     """
    #     Return a mask of the ROI for each fly part
    #     The mask has the same shape as the ROI
    #     and is True on pixels that belong to the part.
    #     The masks are packed in a dictionary.
    #     """

    #     # thresh = cv2.threshold(foreground, self._minimum_change, 255, cv2.THRESH_BINARY)[1]
    #     non_zero = cv2.bitwise_and(foreground, ellipse)

    #     self._fly_pixel_count = np.sum(non_zero)
    #     # median = np.median(foreground[non_zero])
    #     return {"body": non_zero}

    #     # masks = {"core": non_zero < median, "periphery": non_zero > median}
    #     # return masks

    @staticmethod
    def _get_non_overlapping(coords_1, coords_2):
        """
        Count how many pixels are on one of the coordinates sets
        and not the other.
        """

        not_in_2 = sum([coord not in coords_2 for coord in coords_1])
        not_in_1 = sum([coord not in coords_1 for coord in coords_2])

        total_count = not_in_2 + not_in_1
        return total_count

    @staticmethod
    def _document(mask1, mask2):
        cv2.imwrite(os.path.join(home_folder, "mask1.png"), mask1*255)
        cv2.imwrite(os.path.join(home_folder, "mask2.png"), mask2*255)


    def _process_raw_feature(self, raw_feature):
        """
        Make the feature distance-like and normalize with the area of the fly,
        so it can be compared to the centroid displacement variable
        Normalize with the area of the fly to compensate for minor changes
        due to the fly exposing less of its body and viceversa.
        Finally take the log10 and multiply by 1000 to put in the same scale as CD
        as computed in the AdaptiveBGModel GG implementation.
        """
        distance = np.sqrt(raw_feature)
        null_dist = 10 ** (self._null_dist / 1000)
        fly_size_norm = distance / np.sqrt(self._fly_pixel_count)
        roi_width_norm = fly_size_norm * null_dist
        log10_xy_dist_x_1000 = np.log10(roi_width_norm + null_dist) * 1000
        return log10_xy_dist_x_1000

    def extract_features(self, *args, **kwargs):

        datapoints = super().extract_features(*args, **kwargs)

        # if an old foreground is available, compute the features
        # otherwise just return the null movements,
        # defined as 1 / number of pixels on x dimension
        self._new_image = self._gray_original

        if self.old_image is not None:

            # get the old and new coordinates of both parts

            # TODO Use the information about the position of the fly
            # in the datapoints to mask noisy foreground
            # i.e. pixels segmented as foreground but which dont belong to the fly
            # old_body = self._get_body(self.old_image, self.ellipse)
            # new_body = self._get_body(self._new_image, self.ellipse)
            part = "body" 

            # count how many pixels belong to the part on only one but noth both masks
            # xored = np.bitwise_xor(old_body[part], new_body[part])
            diff = cv2.absdiff(self._new_image, self.old_image)
            cv2.bitwise_and(diff, self.ellipse, diff)
            self._fly_pixel_count = np.sum(diff)
            
            diff_segmented = cv2.threshold(diff, self._minimum_change, 255, cv2.THRESH_BINARY)[1]
            diff_bool = diff_segmented == 255
            diff_count = np.sum(diff_bool)

            if self._debug:
                cv2.imwrite(os.path.join(home_folder, "diff", f"ROI-{str(self._roi.idx).zfill(2)}_{str(self._last_t).zfill(10)}.png"), diff)
                cv2.imwrite(os.path.join(home_folder, "diff_segmented", f"ROI-{str(self._roi.idx).zfill(2)}_{str(self._last_t).zfill(10)}.png"), diff_segmented)
                cv2.imwrite(os.path.join(home_folder, "old_body", f"ROI-{str(self._roi.idx).zfill(2)}_{str(self._last_t).zfill(10)}.png"), self.old_image)
                cv2.imwrite(os.path.join(home_folder, "new_body", f"ROI-{str(self._roi.idx).zfill(2)}_{str(self._last_t).zfill(10)}.png"), self._new_image)#, self.ellipse)
            self._last_movements[part] = diff_count

            # instantiate the distances with a wrapper
            # that streamlines saving to output
            body_movement = BodyMovement(self._last_movements["body"])

        else:
            body_movement = BodyMovement(self._null_dist)

        # add the extra features to datapoints and return it
        datapoints[0].append(body_movement)
        return datapoints


    def _track(self, img, *args, **kwargs):
        """
        Extend the abstract's class _track method so it keeps a copy
        of the previous foreground of the fly. This way, the last and previous foregrounds
        can be compared and the extract_features method gets material to work on.
        """

        self.old_ellipse = np.copy(self.ellipse)
        # self.old_image = np.copy(self._buff_fg_backup)
        if len(self._positions) > 0:
            if not self._positions[-1][0]["is_inferred"]:
                self.old_image = self._new_image.copy() # new image is not new anymore actually, since a new one is about to be collected

        shape = img.shape
        # h_im = min(shape)
        w_im = max(shape)
        self._null_dist = round(np.log10(1. / float(w_im)) * 1000)

        datapoints = super()._track(img, *args, **kwargs)
        return datapoints