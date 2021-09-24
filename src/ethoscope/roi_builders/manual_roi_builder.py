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

class ManualROIBuilder(BaseROIBuilder):


    _description = {"overview": "A flmanual exible ROI builder that allows users to enter directly the coordinates of the ROIs",
                    "arguments": [{"type": "str", "name": f"ROI_{i}", "description": f"Coordinates of ROI {i}. Example (1,1), (2,2), (3,3), (4,4). Four coordinates must be passed", "default":""} for i in range(1, NROIS+1)]}

    def __init__(self, coordinates, *args,  **kwargs):
        self._coordinates = coordinates
        super(ManualROIBuilder).__init__(*args,  **kwargs)

    def build(self, img):

        rois = []
        idx = 1

        for coord in self._coordinates:
    
            coord = "[" + coord + "]"
            coord = eval(coord)
            if len(coord) != 4:
                idx += 1
                continue
            cnt = np.array(coord).reshape(4,1,2)
            rois.append(ROI(cnt, idx))
            idx +=1
        
        return rois