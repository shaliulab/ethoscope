__author__ = 'antonio'


__author__ = 'quentin'

import cv2
import unittest
import os
import time
from ethoscope.core.qc import QualityControl
from ethoscope.utils.io import ResultWriter
from ethoscope.roi_builders.target_roi_builder import FSLSleepMonitorWithTargetROIBuilder


try:
    from cv2.cv import CV_AA as LINE_AA
except ImportError:
    from cv2 import LINE_AA

images = {
    "test_1": "../static_files/img/dark_targets_above.png",
    "test_2": "../static_files/img/dark_targets_above_2.png"
}


LOG_DIR = "./test_logs/"

def get_machine_name():
    return "VIRTUAL_ETHOSCOPE"

class TestQC(unittest.TestCase):

    _db_credentials = {
        "name": "%s_db" % get_machine_name(),
        "user": "ethoscope",
        "password": "ethoscope"
    }

    def setUp(self):

        # ROIBuilderClass = roi_builders[args["roi_builder"]]
        ROIBuilderClass = FSLSleepMonitorWithTargetROIBuilder
        roi_builder_kwargs = {}
        self.roi_builder = ROIBuilderClass(**roi_builder_kwargs)

    def test_init(self):

        for path in images.values():
            img = cv2.imread(path)
            rois = self.roi_builder.build(img)
            with ResultWriter(self._db_credentials, rois) as rw:
                rw._max_insert_string_len = 1
                quality_controller = QualityControl(rw)

    def test_qc(self):

        for path in images.values():
            img = cv2.imread(path)
            rois = self.roi_builder.build(img)
            with ResultWriter(self._db_credentials, rois) as rw:
                rw._max_insert_string_len = 1
                quality_controller = QualityControl(rw)
                qc = quality_controller.qc(img)
        
    def test_write(self):
        for path in images.values():
            img = cv2.imread(path)
            rois = self.roi_builder.build(img)
            with ResultWriter(self._db_credentials, rois) as rw:
                rw._max_insert_string_len = 1
                quality_controller = QualityControl(rw)
                qc = quality_controller.qc(img)
                t = time.time()

                quality_controller.write(t, qc)
                quality_controller.flush(t, img)

    def test_pseudostream(self):
        path = images["test_1"]

        img = cv2.imread(path)
        rois = self.roi_builder.build(img)
        with ResultWriter(self._db_credentials, rois) as rw:
            rw._max_insert_string_len = 1
            quality_controller = QualityControl(rw)
            qc = quality_controller.qc(img)
            t = time.time()

            for i in range(100):
                quality_controller.write(t, qc)        
                quality_controller.flush(t, img)





