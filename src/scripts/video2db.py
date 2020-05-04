__author__ = 'quentin'



from ethoscope.hardware.input.cameras import MovieVirtualCamera

# Build ROIs from greyscale image
from ethoscope.roi_builders.fsl_roi_builder import FSLTargetROIBuilder as ROIBuilderClass

# the robust self learning tracker
from ethoscope.trackers.adaptive_bg_tracker import AdaptiveBGModel

from ethoscope.utils.io import SQLiteResultWriter

# the standard monitor
from ethoscope.core.monitor import Monitor

from ethoscope.web_utils.control_thread import ControlThread
from ethoscope.web_utils.helpers import get_git_version

import argparse
import logging
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":

    # run from the src/scripts directory!!!

    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="Input mp4 file", type=str)
    ap.add_argument("--output", help="Resulting sqlite3 db file", type=str)
    ap.add_argument("--machine_id", type=str, default=None)
    ap.add_argument("--name", type=str, default="ETHOSCOPE_CV1")

    ETHOSCOPE_DIR = "/ethoscope_data/results"

    ARGS = vars(ap.parse_args())

    if ARGS["machine_id"] is None:
        # get machine id form filename assuming it is in the third
        # value (0-based index 2) if we split it by underscore 
        MACHINE_ID = ARGS["input"].split("/")[::-1][0].split("_")[2]
    else:
        MACHINE_ID = ARGS["machine_id"]

    NAME = ARGS["name"]
    VERSION = get_git_version()


    data = {
        "camera":
            {"name": "MovieVirtualCamera", "arguments": {"path": ARGS["input"]}},
        "result_writer":
           {"name": "SQLiteResultWriter", "arguments": {"path": ARGS["output"], "take_frame_shots": False}},
        "roi_builder":
           {"name": "FSLTargetROIBuilder", "arguments": {}},
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


