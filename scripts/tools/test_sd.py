import argparse
import logging
import subprocess 
import os

ap = argparse.ArgumentParser()
ap.add_argument("-r", "--region-id", nargs="+", required=True, type=int)
ap.add_argument("--duration", type=int, default=1000)
ap.add_argument("--port", type=int, default=9001)
args = ap.parse_args()


roi_to_channel = {1:1, 3:3, 5:5, 7:7, 9:9, 12:11, 14:13, 16:15, 18:17, 20:19}

channels = [str(roi_to_channel[roi]) for roi in args.region_id]
channels_str = ", ".join(channels)
channels_str = "[" + channels_str + "]"
print(channels_str)
print(channels)
cmd = "/usr/bin/curl -X POST -H \"Content-Type: application/json\" -d '{\"channels\": %s, \"duration\": %d}' localhost:%d/activate" % (channels_str, args.duration, args.port)
os.system(cmd)
print(cmd)
