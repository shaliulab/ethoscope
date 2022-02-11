__author__ = 'quentin'

import numpy as np

import logging
import traceback
import cv2
import os
import time

from ethoscope.utils.description import DescribedObject
from ethoscope.core.roi import ROI
from ethoscope.hardware.input.cameras import OurPiCameraAsync, FSLPiCameraAsync
from ethoscope.configuration import load_config

class BaseROIBuilder(DescribedObject):
    _rois_pickle_file = ''
    _target_coord_file = ''

    def __init__(self):
        """
        Template to design ROIBuilders. Subclasses must implement a ``_rois_from_img`` method.
        """

    @staticmethod
    def fetch_frames(input, mode=None):
        # If input is an image, make a copy
        # Otherwise it is assumed to be a camera object
        # that returns frames upon iterating it.
        # Capture 5 frames and take the median intensity for each pixel
        # i.e. get an image that represents the median of 5 frames


        next_mode = {"target_detection": "roi_builder", "roi_builder": "tracker"}

        config = load_config()
        # modes_min = {"target_detection": 90, "roi_builder": 20, "tracker": 0}
        # modes_n = {"target_detection": 5, "roi_builder": 5}
        # means = {"target_detection": (140, 190), "roi_builder": (20,40)}

        modes_min = config["roi_builder"]["modes_min"]
        modes_n = config["roi_builder"]["modes_n"]
        means = config["roi_builder"]["means"]

        accum = []
        if isinstance(input, np.ndarray):
            accum = np.copy(input)

        else:
            i = 0
            for x in input:

                _, (t_ms, frame) = x

                output_path = "/root/frame_%s.png" % (str(i).zfill(4))
                cv2.imwrite(output_path, frame)
                logging.warning(f"ROI builder frame number: {i}")
                logging.warning(f"mean_intensity: {np.mean(frame)}")
                if i  == modes_n[mode]-1:
                    break
                if mode is not None:

                    mean_intensity = np.mean(frame)
                    i = input.change_gain(mean_intensity=mean_intensity, means=means, mode=mode, i=i)                    
                    if mean_intensity < modes_min[mode]:
                        modes_n[next_mode[mode]] -= 1

                accum.append(frame)

            accum = np.median(np.array(accum),0).astype(np.uint8)

        output_path = os.path.join(os.environ["HOME"], f"{mode}_input.png")
        logging.info(f"Saving {mode} accum to {output_path}")
        cv2.imwrite(output_path, accum)

        return accum

    def build(self, input):
        """
        Uses an input (image or camera) to build ROIs.
        When a camera is used, several frames are acquired and averaged to build a reference image.

        :param input: Either a camera object, or an image.
        :type input: :class:`~ethoscope.hardware.input.camera.BaseCamera` or :class:`~numpy.ndarray`
        :return: list(:class:`~ethoscope.core.roi.ROI`)
        """

        accum = self.fetch_frames(input, mode="target_detection")

        try:
            if self.__class__.__name__ == "HighContrastTargetRoiBuilder":
                img, M, rois = self._rois_from_img(accum, camera=input)
            else:
                rois = self._rois_from_img(accum)
                img = accum


            try:
                roi_build_with_dots = img.copy()
                for pt in self._sorted_src_pts:
                    roi_build_with_dots = cv2.circle(roi_build_with_dots, tuple(pt), 5, (0,255,0), -1)

                cv2.imwrite(os.path.join(os.environ["HOME"], "roi_build_with_dots.png"), roi_build_with_dots)
            except AttributeError as e:
                logging.warning(e)


        except Exception as e:
            if not isinstance(input, np.ndarray):
                del input
            logging.error(traceback.format_exc())
            raise e

        rois_w_no_value = [r for r in rois if r.value is None]

        if len(rois_w_no_value) > 0:
            rois = self._spatial_sorting(rois)
        else:
            rois = self._value_sorting(rois)

        if self.__class__.__name__ == "FSLTargetROIBuilder":
            result = (img, M, rois)
        else:
            result = rois

        return result



    def _rois_from_img(self,img):
        raise NotImplementedError

    def _spatial_sorting(self, rois):
        '''
        returns a sorted list of ROIs objects it in ascending order based on the first value in the rectangle property
        '''
        return sorted(rois, key=lambda x: x.rectangle[0], reverse=False)

    def _value_sorting(self, rois):
        '''
        returns a sorted list of ROIs objects it in ascending order based on the .value property
        '''
        return sorted(rois, key=lambda x: x.value, reverse=False)


class DefaultROIBuilder(BaseROIBuilder):


    """
    The default ROI builder. It simply defines the entire image as a unique ROI.
    """
    _description = {"overview": "The default ROI builder. It simply defines the entire image as a unique ROI.", "arguments": []}


    def _rois_from_img(self,img):
        h, w = img.shape[0],img.shape[1]
        return[
            ROI(np.array([
                (   0,        0       ),
                (   0,        h -1    ),
                (   w - 1,    h - 1   ),
                (   w - 1,    0       )])
            , idx=1)]

