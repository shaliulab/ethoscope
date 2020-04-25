__author__ = 'quentin'

import cv2
import unittest
import os
import pickle
import datetime
import time
import sys
from ethoscope.utils.debug import EthoscopeException

from ethoscope.roi_builders.target_roi_builder import FSLSleepMonitorWithTargetROIBuilder, SleepMonitorWithTargetROIBuilder, TargetGridROIBuilder
print(os.getcwd())

try:
    from cv2.cv import CV_AA as LINE_AA
except ImportError:
    from cv2 import LINE_AA

images = {
           "test_qc": "../static_files/img/dark_targets_above.png",
           "test_light": "../static_files/img/light.png"}


LOG_DIR = "./test_logs/"

class TestTargetROIBuilder(unittest.TestCase):

    roi_builder = SleepMonitorWithTargetROIBuilder()
    
    
    def setUp(self):
        
        self.class_name = self.__class__.__name__
        print(self.class_name)


    def _draw(self,img, rois, arena=None):
        for r in rois:
            cv2.drawContours(img,r.polygon,-1, (255,255,0), 2, LINE_AA)


        if arena is not None:
            pass
            # cv2.drawContours(img,[arena],-1, (255,255,0), 2, LINE_AA)




    def _test_live(self):

        if self._path is None:

            import picamera
            import io
            import numpy as np
            from PIL import Image
            stream = io.BytesIO()
    
            with picamera.PiCamera() as cam:
                cam.start_preview()
                time.sleep(2)
                cam.capture(stream, format='jpeg')
                stream.seek(0)
                image = Image.open(stream)
                img = np.asarray(image)

        else:
            
            img = cv2.imread(self._path)
            

        try:
            img, rois = self.roi_builder.build(img)
            
        except EthoscopeException:
            cv2.imwrite(f'/tmp/fail_rois_{self.message}.png',img)
            return

        self._draw(img, rois)
        cv2.imwrite(f'/tmp/rois_{self.message}.png',img)
        #self.assertEqual(len(rois),20)



    def _test_one_img(self,path, out):
        
        img = cv2.imread(path)
        
        rois = self.roi_builder.build(img)
        angle = self.roi_builder._angle
        M = self.roi_builder._M
        arena = self.roi_builder._arena
        
        img = cv2.warpAffine(img, self.roi_builder._M, img.shape[:2][::-1], flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        pickle_file = os.path.join(LOG_DIR, self.class_name + "_rois.pickle")
        with open(pickle_file, "wb") as fh:
            pickle.dump(rois, fh)
        self._draw(img, rois, arena)
        if out is None:
            out = os.path.join(LOG_DIR, f'{now}_annot.png')
        cv2.imwrite(out,img)
        self.assertEqual(len(rois),20)


    def test_all(self):

        for k,i in list(images.items()):
            out = os.path.join(LOG_DIR,self.class_name +".png")
            print(out)
            self._test_one_img(i,out)


class TestFSLROIBuilder(TestTargetROIBuilder):

    roi_builder = FSLSleepMonitorWithTargetROIBuilder()



if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('-m', '--message', help='Message is written to the output file as a suffix')
    ap.add_argument('-p', '--path', help='Path to image to test the ROI Builder against')
    args = vars(ap.parse_args())
    print(args)
    message = args['message']
    TestFSLROIBuilder.message = message
    test_instance = TestFSLROIBuilder()
    if args['path'] is not None:
        test_instance._path = args['path']
    test_instance.setUp()
    test_instance._test_live()

    

