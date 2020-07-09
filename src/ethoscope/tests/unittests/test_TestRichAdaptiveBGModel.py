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
from ethoscope.core.roi import ROI

LOG_DIR = "./test_logs/"

class TestRichAdaptiveBGModel(unittest.TestCase):

    def setUp(self):

        self._result = []

        # head is moving
        # self._videos = ["../static_files/videos/whole_2020-05-09_12-00-07_014aad42625f433eb4bd2b44f811738e__1280x960@12_00000__ROI18@t003470000.avi"]
        # self._videos = ["../static_files/videos/whole_2020-05-09_12-00-07_014aad42625f433eb4bd2b44f811738e__1280x960@12_00000__ROI20@t013210000.avi"]
        # flipping wings
        self._videos = ["../static_files/videos/whole_2020-05-09_12-00-07_014aad42625f433eb4bd2b44f811738e__1280x960@12_00000__ROI15@t007190000.avi"]
        # pretty still
        # self._videos = ["../static_files/videos/whole_2020-05-09_12-00-07_014aad42625f433eb4bd2b44f811738e__1280x960@12_00000__ROI07@t004550000.avi"]
        self.roi = None
        self.camera = FSLVirtualCamera(path=self._videos[0], bw=False, use_wall_clock=False)

        for frame_idx, (t_ms, img) in self.camera:
            print(frame_idx)

            # cv2.imshow("img", img)
            # cv2.waitKey(0)

            if self.roi is None:
                shape = img.shape
                shape = tuple([e-1 for e in shape])

                self.roi = ROI(np.array([(0, 0), (shape[1], 0), shape[:2][::-1], (0, shape[0])]), idx=18)
                self.tracker = RichAdaptiveBGModel(roi=self.roi)
                self.tracker.live_tracking = True
                self.tracker._old_pos = 0.0+0.0j
                self.tracker._null_dist = round(np.log10(1. / float(img.shape[1])) * 1000)

                try:
                    datapoints = self.tracker.track(t_ms, img)
                except NoPositionError:
                    pass
            # print(img.shape)
            datapoints = self.tracker.track(t_ms, img)
            if datapoints:
                self._result.append((t_ms, datapoints))

if __name__ == '__main__':
    # import argparse
    # ap = argparse.ArgumentParser()
    # ap.add_argument('-m', '--message', help='Message is written to the output file as a suffix')
    # ap.add_argument('-p', '--path', help='Path to image to test the ROI Builder against')
    # ap.add_argument('-target_coordinates', help='Path to file with coordinates of 3 targets in frame', required=False, default='/etc/target_coordinates.conf')
    # args = vars(ap.parse_args())
    # print(args)

    import matplotlib.pyplot as plt

    test_instance = TestRichAdaptiveBGModel()
    test_instance.setUp()
    x = [e[0] for e in test_instance._result]
    print(test_instance._result[0])
    y1 = [e[1][0]["core_movement"] for e in test_instance._result]
    y2 = [e[1][0]["xy_dist_log10x1000"] for e in test_instance._result]
    # import ipdb; ipdb.set_trace()
    plt.scatter(x=x, y=y1, color="blue", label="movement")
    plt.scatter(x=x, y=y2, color="red", label="distance")
    plt.hlines(y=np.log10(0.048) * 1000, xmin=x[0], xmax=x[-1])
    plt.hlines(y=np.log10(0.003) * 1000, xmin=x[0], xmax=x[-1])
    plt.legend(loc="upper_left")
    plt.savefig("/home/vibflysleep/scatter.png")


    # plt.plot(x, y1, "bo-", label="movement")
    # plt.plot(x, y2, "ro-", label="distance")
    # plt.legend(loc="upper_left")
    plt.savefig("/home/vibflysleep/plot.png")
