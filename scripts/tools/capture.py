import time
import tempfile
import logging
import numpy as np
logging.basicConfig(level=logging.INFO)

from picamera import PiCamera
from picamera.array import PiRGBArray
import cv2
from ethoscope.hardware.input.camera_settings import configure_camera

try:
    from ethoscope.web_utils.helpers import get_machine_name
    machine_name = get_machine_name()
    prefix = machine_name + "_"
except ImportError:
    prefix = ""

suffix = ".png"
temp = tempfile.NamedTemporaryFile(prefix = prefix, suffix=".png", delete=False)

with PiCamera(framerate=12, resolution=(1280,960)) as capture:
    capture.resolution = (1024, 768)
    capture = configure_camera(capture, mode = "target_detection")

    time.sleep(2)

    logging.warning(f'camera framerate: {capture.framerate}')
    logging.warning(f'camera resolution: {capture.resolution}')
    logging.warning(f'camera exposure_mode: {capture.exposure_mode}')
    logging.warning(f'camera shutter_speed: {capture.shutter_speed}')
    logging.warning(f'camera exposure_speed: {capture.exposure_speed}')
    logging.warning(f'camera awb_gains: {capture.awb_gains}')
    logging.warning(f'camera analog_gain: {float(capture.analog_gain)}')
    logging.warning(f'camera digital_gain: {float(capture.digital_gain)}')


    raw_capture = PiRGBArray(capture, size=capture.resolution)
    
    for frame in capture.capture_continuous(raw_capture, format="bgr", use_video_port=True):
        raw_capture.truncate(0)
        out = cv2.cvtColor(frame.array,cv2.COLOR_BGR2GRAY)
        mean_intensity = np.mean(out)
        break


logging.info(f"Saving capture to {temp.name}")
logging.info(f"Intensity is {mean_intensity}")
cv2.imwrite(temp.name, out)
cv2.imwrite("/tmp/last_img.png", out)

