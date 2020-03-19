from benchmark_helpers import benchmark_camera
import argparse
import logging
import sys
logger = logging.getLogger('__main__')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

ap = argparse.ArgumentParser()

ap.add_argument('-f', '--framerate', type = int, default=10)
#ap.add_argument('-f', '--framerate', type = float, default=10.0)
ap.add_argument('-r', '--resolution', type = str, default='1280x960')
ap.add_argument('-s', '--shutter_speed', type = int, default=None)
ap.add_argument('-i', '--iso', type = int, default=0)
ap.add_argument('-a', '--awb_gains', type = str, default=None)
ap.add_argument('-l', '--preview_length', type = int, default=100)

args = vars(ap.parse_args())

logger.info(args)

target_fps = args['framerate']
preview_length  = args['preview_length']
target_resolution= [int(e) for e in args['resolution'].split('x')]
shutter_speed = args['shutter_speed']
iso = args['iso']
if args['awb_gains'] is None:
    awb_mode = 'auto'
    awb_gains = None

else:
    awb_mode = 'off'
    awb_gains = [float(e) for e in args['awb_gains'].split(',')]

if args['shutter_speed'] is None:
    exposure_mode = 'auto'
else:
    exposure_mode = 'off'

benchmark_camera(target_fps, target_resolution, awb_gains, awb_mode, shutter_speed, exposure_mode, iso, preview_length)
logger.info("Done")

