from ethoscope.core.roi import ROI

__author__ = 'quentin'

import numpy as np

import logging
import traceback
import cv2
from ethoscope.utils.description import DescribedObject


class BaseROIBuilder(DescribedObject):

    def __init__(self):
        """
        Template to design ROIBuilders. Subclasses must implement a ``_rois_from_img`` method.
        """
        pass


    @staticmethod
    def fetch_frames(input):
        # If input is an image, make a copy
        # Otherwise it is assumed to be a camera object
        # that returns frames upon iterating it.
        # Capture 5 frames and take the median intensity for each pixel
        # i.e. get an image that represents the median of 5 frames
        accum = []
        if isinstance(input, np.ndarray):
            accum = np.copy(input)

        else:
            for i, (_, frame) in enumerate(input):
                accum.append(frame)
                logging.warning(f"I: {i}")
                logging.warning(f"mean_intensity: {np.mean(frame)}")
                if i  == 4:
                    break
            accum = np.median(np.array(accum),0).astype(np.uint8)

        cv2.imwrite("/root/target_detection_fetch_frames.png", accum)
        
        return accum

    def build(self, input):
        """
        Uses an input (image or camera) to build ROIs.
        When a camera is used, several frames are acquired and averaged to build a reference image.

        :param input: Either a camera object, or an image.
        :type input: :class:`~ethoscope.hardware.input.camera.BaseCamera` or :class:`~numpy.ndarray`
        :return: list(:class:`~ethoscope.core.roi.ROI`)
        """

        accum = self.fetch_frames(input)     

        try:
            if self.__class__.__name__ == "FSLTargetROIBuilder":
                cv2.imwrite("/root/target_detection_build.png", accum)
                img, M, rois = self._rois_from_img(accum, camera=input)
            else:
                rois = self._rois_from_img(accum)

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

