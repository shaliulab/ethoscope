import time
import logging
import argparse
import datetime

import numpy as np
import cv2
import picamera
import picamera.array

import argparse
from .backends import opencv_backend, imgstore_backend


logging.basicConfig(level=logging.INFO)

video_writer = None

def get_parser():

    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["opencv", "imgstore"], default="opencv")
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--height", type=int, required=True)
    ap.add_argument("--framerate", type=float, default=30.0)
    ap.add_argument("--chunk-duration", type=int, default=300, dest="chunk_duration")
    ap.add_argument("--duration", type=int, default=24*3600)
    return ap


def capture_imgstore(resolution=(4064, 3040), framerate=30.0, duration=24*3600, chunk_duration=300):
    return capture_continuous(resolution, framerate=framerate, backend=imgstore_backend, video_port=False, shutter_speed=2000, exposure_mode="off", awb_mode="off", awb_gains=(1.8, 1.5), duration=duration, chunk_duration=chunk_duration)


def capture_video(resolution=(1280, 960), framerate=30.0, duration=24*3600, chunk_duration=300):
    return capture_continuous(resolution, framerate=framerate, backend=opencv_backend, video_port=True, shutter_speed=2000, exposure_mode="off", awb_mode="off", awb_gains=(1.8, 1.5), duration=duration, chunk_duration=chunk_duration)

def capture_img(resolution=(4064, 3040), framerate=30.0, duration=24*3600, chunk_duration=300):
    return capture_continuous(resolution, framerate=framerate, backend=opencv_backend, video_port=False, shutter_speed=2000, exposure_mode="off", awb_mode="off", awb_gains=(1.8, 1.5), duration=duration, chunk_duration=chunk_duration)

def capture_continuous(resolution, framerate=30.0, backend=opencv_backend, video_port=True, duration=24*3600, chunk_duration=300, **kwargs):
    """
    The RPi HQ camera cannot capture better resolution than 1280x960
    when recording a video
    """

    global video_writer
    frame_count = 0
    chunk_count = 0
    start_time = time.time()

    shutter_speed = kwargs.pop("shutter_speed")
    exposure_mode = kwargs.pop("exposure_mode")
    awb_mode = kwargs.pop("awb_mode")
    awb_gains = kwargs.pop("awb_gains")

    
    with picamera.PiCamera(resolution=resolution, framerate=framerate, **kwargs) as camera:
        camera.awb_mode = "off"
        camera.awb_gains = (1.8, 1.5)
        camera.annotate_text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        camera.exposure_mode = exposure_mode 
        camera.shutter_speed = shutter_speed
        camera.awb_mode = awb_mode
        camera.awb_gains = awb_gains
    
        stream = picamera.array.PiRGBArray(camera, size=resolution)
    
        for i, frame in enumerate(camera.capture_continuous(stream, format="bgr", use_video_port=video_port)):
            frame_count += 1
            if not backend(stream, i, frame, resolution=resolution, framerate=framerate,
                    start_time=start_time, duration=duration, video_writer=video_writer,
                    chunk_count=chunk_count, chunk_duration=chunk_duration, frame_count=frame_count
                    ):
                break



    return 0

def main():
    ap = get_parser()
    args = ap.parse_args()

    resolution = (args.width, args.height)
    framerate = args.framerate

    duration = args.duration
    chunk_duration = args.chunk_duration

    if args.backend == "opencv":
        capture_img(resolution, framerate, duration, chunk_duration)
    elif args.backend == "imgstore":
        capture_imgstore(resolution, framerate, duration, chunk_duration)
    else:
        raise Exception("Invalid backend")


if __name__ == "__main__":
    main()
