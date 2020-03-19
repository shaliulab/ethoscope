import picamera
from picamera.array import PiRGBArray
import logging
import cv2
import time

target_fps=20
target_resolution=(1280, 960)

with picamera.PiCamera() as capture:

    logging.warning(capture)

    capture.resolution = target_resolution
    #capture.awb_mode = 'auto'
    capture.awb_mode = 'off'
    capture.awb_gains = (1.8, 1.5)
    capture.framerate = target_fps
    raw_capture = PiRGBArray(capture, size = target_resolution)
    for frame in capture.capture_continuous(raw_capture, format="bgr", use_video_port=True):

        try:
            raw_capture.truncate(0)
            #out = cv2.cvtColor(frame.array, cv2.COLOR_BGR2GRAY)
            out = frame.array
            cv2.imwrite('/tmp/last_img.png', out)
            time.sleep(2)

        except Exception as e:
            logging.warning(e)
            break
