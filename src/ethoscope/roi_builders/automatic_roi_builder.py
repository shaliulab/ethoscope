__author__ = 'antonio'

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
logging.basicConfig(level=logging.INFO)
from ethoscope.roi_builders.roi_builders import BaseROIBuilder
from ethoscope.core.roi import ROI
from ethoscope.utils.debug import EthoscopeException
import itertools
import os
from ethoscope.roi_builders.helpers import *

NROIS = 20

class AutomaticROIBuilder(BaseROIBuilder):


    _description = {"overview": "A flmanual exible ROI builder that allows users to enter directly the coordinates of the ROIs",
            "arguments": [
                {"type": "str", "name": "top_left", "description": "Coordinates of top left corner. Example: (0, 0).", "default":"(0,0)"},
                {"type": "number", "name": "roi_width", "description": "Width of ROIs", "default": 978}, 
                {"type": "number", "name": "roi_height", "description": "Height of ROIs", "default": 86}, 
                {"type": "number", "name": "roi_offset", "description": "Vertical displacement of ROIs", "default": 110}, 
                {"type": "number", "name": "nrois", "description": "Number of ROIs", "default": 9}, 
                ]}

    def __init__(self, args,  kwargs):

        self._coordinates = []
        nrois = kwargs.pop("nrois")
        width = kwargs.pop("roi_width")
        height = kwargs.pop("roi_height")
        offset = kwargs.pop("roi_offset")
        top_left = kwargs.pop("top_left")
        tl = eval(top_left)
        self._coordinates = [f"({tl[0]}, {tl[1] + offset*i}), ({tl[0]+width}, {tl[1] + offset*i}),({tl[0]+width}, {tl[1]+height + offset*i}), ({tl[0]}, {tl[1]+height + offset*i})" for i in range(nrois)]
        logging.warning(self._coordinates)
        super(AutomaticROIBuilder, self).__init__()

    def build(self, cam):

        rois = []
        idx = 1
        try:
            cam.set_roi_builder()
        except Exception:
            pass

        for coord in self._coordinates:
    
            coord = "[" + coord + "]"
            coord = eval(coord)
            if len(coord) != 4:
                idx += 1
                continue
            cnt = np.array(coord).reshape(4,1,2)
            width, height = cam.resolution
            cnt[:, :, 0] = np.array([[width, ] * 4, cnt[:,:,0]]).min(axis=0)
            cnt[:, :, 1] = np.array([[height, ] * 4, cnt[:,:,1]]).min(axis=0)
            rois.append(ROI(cnt, idx))
            idx +=1

        try:
            cam.set_tracker()
        except Exception:
            pass
        
        logging.warning(rois)
        return rois
