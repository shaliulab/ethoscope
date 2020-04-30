import time
import tempfile
import logging
logging.basicConfig(level=logging.INFO)

from picamera import PiCamera
from picamera.array import PiRGBArray
import cv2

try:
    from ethoscope.web_utils.helpers import get_machine_name
    machine_name = get_machine_name()
    prefix = machine_name + "_"
except ImportError:
    prefix = ""

suffix = ".png"
temp = tempfile.NamedTemporaryFile(prefix = prefix, suffix=".png", delete=False)

with PiCamera() as capture:
    capture.resolution = (1024, 768)
    capture.awb_mode = "off"
    time.sleep(1)
    capture.awb_gains = (1.8, 1.5)
    capture.exposure_mode = "off"
    time.sleep(1)
    capture.shutter_speed = 50000
    raw_capture = PiRGBArray(capture, size=capture.resolution)
    
    for frame in capture.capture_continuous(raw_capture, format="bgr", use_video_port=True):
        raw_capture.truncate(0)
        out = cv2.cvtColor(frame.array,cv2.COLOR_BGR2GRAY)
        break


logging.info(f"Saving capture to {temp.name}")
cv2.imwrite(temp.name, out)

