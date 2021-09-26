import picamera
from picamera.array import PiRGBArray
import logging
import cv2
import time
import numpy as np
import os
import os.path
import argparse
import sys
from tqdm import tqdm
home_folder = os.environ["HOME"]


logger = logging.getLogger('__main__')

def benchmark_camera(target_fps, target_resolution, awb_gains, awb_mode, shutter_speed, exposure_mode, iso, preview_length=100): 

    i = 0
    j = 0
    attrs = ['t','analog_gain', 'digital_gain', 'exposure_speed', 'shutter_speed', 'iso', 'framerate', 'resolution', 'awb_gains']

    cache_length= 10
    cache = [None,] * cache_length

    if awb_gains is None:
        filename = f'camera_stats_@{target_fps}fps_{"x".join([str(e) for e in target_resolution])}_{shutter_speed}shutter_{iso}iso_Noneawb.txt'
    else:
        filename = f'camera_stats_@{target_fps}fps_{"x".join([str(e) for e in target_resolution])}_{shutter_speed}shutter_{iso}iso_{",".join([str(f) for f in awb_gains])}awb.txt'
    file_path = os.path.join(home_folder, 'benchmark_camera', filename)
    logger.info(f"Saving results to {file_path}")


    # Test camera settings and relation between them
    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass



    with open(file_path, 'a+') as fh:
        fh.write('t,analog_gain,digital_gain,exposure_speed,shutter_speed,iso,framerate,width,height,red,blue\n')
        t0 = time.time()

        with picamera.PiCamera() as camera:
        
            camera.framerate = target_fps
            camera.resolution = target_resolution
            camera.awb_mode = awb_mode
            if awb_mode == 'off':
                camera.awb_gains = awb_gains
    
            if exposure_mode == 'off':
                camera.shutter_speed = shutter_speed
                camera.exposure_mode = 'off'
    
            raw_camera = PiRGBArray(camera, size = target_resolution)

            cache_idx = 0
            iter_idx = 0
    
            with tqdm(total=preview_length, file=sys.stdout) as pbar:
                for frame in camera.capture_continuous(raw_camera, format='bgr', use_video_port=True):
                    raw_camera.truncate(0)
                    t = time.time() - t0
                    #logging.info(f't elapsed: {t}')
   
                    attr_idx = 0 
                    row = [None] * len(attrs)
                    for attr in attrs:
                        if attr_idx == 0:
                            row[0] = str(t)
                            attr_idx += 1
                            continue
   
                        try:
                            value = float(getattr(camera, attr, None))
                        except TypeError:
                            value = getattr(camera, attr, None)
            
                        if not attr in ['awb_gains', 'resolution']:
                            row[attr_idx] = str(float(value))
                        elif attr == 'awb_gains':
                            red_gain = str(float(value[0].numerator / value[0].denominator))
                            blue_gain = str(float(value[1].numerator / value[1].denominator))
                            row[attr_idx] = ','.join([red_gain, blue_gain]) 
        
                        elif attr == 'resolution':
                            width = str(float(value[0]))
                            height = str(float(value[1]))
                            row[attr_idx] = ','.join([width, height]) 
   
                        attr_idx += 1
                    # end for loop of attrs

                    if cache_idx == (cache_length-1):
                        cache[cache_idx] = row
                        list_of_rows = [','.join(row) for row in cache]
                        to_write = '\n'.join(list_of_rows)
                        fh.write(to_write + "\n")
                        cache = [None] * cache_length
                        cache_idx = 0
                         
                    else:
                        cache[cache_idx] = row
                        cache_idx += 1
                        
                    pbar.update(1)
                    iter_idx += 1

                    if iter_idx == preview_length:
                        return None


    
                # end for loop
