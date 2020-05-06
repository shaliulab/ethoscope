__author__ = 'quentin'

import argparse
import logging
import os.path
logging.basicConfig(level=logging.INFO)

from ethoscope.web_utils.control_thread import ControlThread
from ethoscope.web_utils.helpers import get_git_version

if __name__ == "__main__":

    # run from the src/scripts directory!!!

    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", help="Input mp4 file", type=str)
    ap.add_argument("-o", "--output", help="Resulting sqlite3 db file", type=str)
    ap.add_argument("--machine_id", type=str, required=False)
    ap.add_argument("--name", type=str, default="ETHOSCOPE_CV1")
    ap.add_argument("-r", "--roi_builder", type=str, default="FSLTargetROiBuilder")
    ap.add_argument("-t", "--target_coordinates_file", type=str, required=False)

    ETHOSCOPE_DIR = "/ethoscope_data/results"

    ARGS = vars(ap.parse_args())

    if ARGS["machine_id"] is None:
        # get machine id form filename assuming it is in the third
        # value (0-based index 2) if we split it by underscore
        MACHINE_ID = ARGS["input"].split("/")[::-1][0].split("_")[3]
    else:
        MACHINE_ID = ARGS["machine_id"]


    NAME = ARGS["name"]
    VERSION = get_git_version()

    if ARGS["output"] is None:
        DATE = ARGS["input"].split("/")[::-1][1]
        OUTPUT = os.path.join(ETHOSCOPE_DIR, MACHINE_ID, NAME, DATE, DATE + "_" + MACHINE_ID + ".db")
    else:
        OUTPUT = ARGS["output"]


    data = {
        "camera":
            {"name": "MovieVirtualCamera", "arguments": {"path": ARGS["input"]}},
        "result_writer":
           {"name": "SQLiteResultWriter", "arguments": {"path": OUTPUT, "take_frame_shots": False}},
        "roi_builder":
        {"name": ARGS["roi_builder"], "arguments": {"target_coordinates_file": ARGS["target_coordinates_file"]}},
    }

    control = ControlThread(MACHINE_ID, NAME, VERSION, ethoscope_dir=ETHOSCOPE_DIR, data=data, verbose=True)
    control.start()

    # # this replicates the code in ControlThread._set_tracking_from_scratch
    # cam=MovieVirtualCamera(ARGS["input"])

    # roi_builder=ROIBuilderClass()

    # try:
    # if roi_builder.__class__.__name__ == "FSLTargetROIBuilder":
    #     img, M, rois=roi_builder.build(cam)
    # else:
    #     rois=roi_builder.build(cam)
    #     M=None

    # self._metadata={
    #     "machine_id": self._info["id"],
    #     "machine_name": self._info["name"],
    #     "date_time": cam.start_time,  # the camera start time is the reference 0
    #     "frame_width": cam.width,
    #     "frame_height": cam.height,
    #     "version": self._info["version"]["id"],
    #     "experimental_info": str(self._info["experimental_info"]),
    #     "selected_options": str(self._option_dict),
    # }
    # # hardware_interface is a running thread
    # rw=ResultWriterClass(self._db_credentials, rois, self._metadata, take_frame_shots=True, sensor=sensor)


    # monit=Monitor(cam,
    #                 AdaptiveBGModel,
    #                 rois,
    #                 out_file=ARGS["out"], # save a csv out
    #                 max_duration=ARGS["duration"], # when to stop (in seconds)
    #                 video_out=ARGS["result_video"], # when to stop (in seconds)
    #                 draw_results=True, # draw position on image
    #                 draw_every_n=1) # only draw 1 every 10 frames to save time
    # monit.run()


