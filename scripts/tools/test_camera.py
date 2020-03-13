import picamera
from picamera.array import PiRGBArray
import logging
import cv2
import time

target_fps=2
target_resolution=(1280, 960)

i = 0
with picamera.PiCamera() as camera:
    camera.framerate = target_fps
    camera.resolution = target_resolution
    raw_camera = PiRGBArray(camera, size = target_resolution)
    for frame in camera.capture_continuous(raw_camera, format='bgr', use_video_port=True):
        for attr in ['analog_gain', 'digital_gain', 'exposure_speed', 'shutter_speed', 'iso', 'framerate', 'resolution']:
            try:
                value = float(getattr(camera, attr, None))
            except TypeError:
                value = getattr(camera, attr, None)
    
            logging.warning(f'{attr}: {value}')

        try:
            raw_camera.truncate(0)
            out = frame.array
            cv2.imwrite(f'/tmp/last_img_{i}.png', out)
            if i == 3:
                i = 0
            else:
                i += 1
        except Exception as e:
            break


    
    
    
