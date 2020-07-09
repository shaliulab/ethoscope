__author__ = 'antonio'

import cv2
import unittest
import os
import pickle
import datetime
import time
import sys
from ethoscope.utils.debug import EthoscopeException

import numpy as np

from ethoscope.trackers.rich_adaptive_bg_tracker import RichAdaptiveBGModel
from ethoscope.hardware.input.cameras import FSLVirtualCamera
from ethoscope.trackers.trackers import NoPositionError

LOG_DIR = "./test_logs/"

class TestRichAdaptiveBGModelFromForeground(unittest.TestCase):

    def setUp(self):

        self._result = []
        self._videos = ["../static_files/videos/2020-06-21_18-39-20_029aad42625f433eb4bd2b44f811738e_ROI_14_FOREGROUND.avi"]
        self._pickle_file = "../static_files/pickle/2020-06-21_18-39-20_029aad42625f433eb4bd2b44f811738e_rois.pickle"
        with open(self._pickle_file, "rb") as fh:
            rois = pickle.load(fh)

        roi = [roi for roi in rois if roi.idx == 14][0]

        self.camera = FSLVirtualCamera(path=self._videos[0], bw=True, use_wall_clock=False)
        self.tracker = RichAdaptiveBGModel(roi=roi)
        self.tracker.live_tracking = False
        self.tracker._old_pos = 0.0+0.0j

        self.old_foreground = None

        for frame_idx, (t_ms, img) in self.camera:

            print(img.shape)
            self.tracker._buff_fg = img
            self.tracker._buff_fg_backup = np.copy(img)
            self.tracker._null_dist = round(np.log10(1. / float(img.shape[1])) * 1000)

            if self.old_foreground is None:
                pass
            else:
                try:
                    hull, is_ambiguous = self.tracker.get_hull()
                except NoPositionError:
                    self.old_foreground = np.copy(img)
                    continue
                data_points = self.tracker.extract_features(self.old_foreground, hull)
                print(data_points)
                self._result.append(data_points)

            self.old_foreground = np.copy(img)


if __name__ == '__main__':
    # import argparse
    # ap = argparse.ArgumentParser()
    # ap.add_argument('-m', '--message', help='Message is written to the output file as a suffix')
    # ap.add_argument('-p', '--path', help='Path to image to test the ROI Builder against')
    # ap.add_argument('-target_coordinates', help='Path to file with coordinates of 3 targets in frame', required=False, default='/etc/target_coordinates.conf')
    # args = vars(ap.parse_args())
    # print(args)

    import matplotlib.pyplot as plt

    test_instance = TestRichAdaptiveBGModelFromForeground()
    test_instance.setUp()
    x = [i for i in range(len(test_instance._result))]
    y1 = [e[0]["core_movement"] for e in test_instance._result]
    y2 = [e[0]["xy_dist_log10x1000"] for e in test_instance._result]
    import ipdb; ipdb.set_trace()
    plt.scatter(x=x, y=y1, color="blue")
    plt.scatter(x=x, y=y2, color="red")
    plt.savefig("/home/vibflysleep/scatter.png")

    plt.plot(x, y1, "bo-")
    plt.plot(x, y2, "ro-")
    plt.savefig("/home/vibflysleep/plot.png")
