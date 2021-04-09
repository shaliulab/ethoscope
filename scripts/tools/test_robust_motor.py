import time
import argparse
import logging
from ethoscope.hardware.interfaces.optomotor import SleepDepriver

ap = argparse.ArgumentParser()

ap.add_argument("-r", "--region-id", nargs="+", required=True)
ap.add_argument("--duration", type=int, help="Duration in ms", default=1000)
ap.add_argument("--wait", type=int, help="Dead time in ms", default=0)
args = ap.parse_args()
print(args)


sd = SleepDepriver(do_warm_up=False)
roi_to_channel = {1:1, 3:3, 5:5, 7:7, 9:9, 12:11, 14:13, 16:15, 18:17, 20:19}


for roi in args.region_id:
    roi = int(roi)
    try:
        channel = roi_to_channel[roi]
    except KeyError:
        logging.warning("ROI %d is not connected to any motor. Ignoring...", roi)
        continue
    sd.activate(channel=channel, duration=args.duration)
    print("Waiting %i seconds" % (args.wait / 1000))
    time.sleep(args.wait / 1000)
