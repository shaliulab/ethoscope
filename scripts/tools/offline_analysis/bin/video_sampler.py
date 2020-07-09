#! /home/vibflysleep/anaconda3/envs/ethoscope3.7/bin/python

r"""
Sample videos of small duration from an input video
using the windows provided in a metadata.csv file
The file should have no headers and just two columns:
start and end seconds of each window, row by row.
"""
import argparse
import logging
import os
import os.path
# import time
from shutil import copyfile
import traceback

import pandas as pd

from ethoscope.hardware.input.cameras import FSLVirtualCamera, MovieVirtualCamera
from ethoscope_node.utils.time_window import TimeWindow
CAMERAS = {cl.__name__ : cl for cl in [FSLVirtualCamera, MovieVirtualCamera]}

logging.basicConfig(level=logging.INFO)


def main(ARGS):

    INPUT = ARGS["input"]
    FPS = ARGS["framerate"]
    ALL = ARGS["all"]
    METADATA = ARGS["metadata"]
    ## Initialize camera with arguments provided by user
    DATA = {
            "name": ARGS["camera"],
            "args": (INPUT,),
            "kwargs": {"use_wall_clock": False}
    }


    # if output is not given, set it to a dir inside videos
    # with same struture as videos
    # i.e. machine_id/machine_name/date_time/files
    if ARGS["output"] is None:
        OUTPUT = os.path.dirname(INPUT).replace("videos", "videos/samples")
    else:
        OUTPUT = ARGS["output"]

    os.makedirs(OUTPUT, exist_ok=False)
    # copy the metadata to the result folder so it is never lost
    DST = os.path.join(OUTPUT, os.path.basename(METADATA))
    logging.info("Copying metadata to %s", DST)
    copyfile(METADATA, DST)

    # Define the camera class that will be used to screen the fragments
    CameraClass = CAMERAS[DATA["name"]]
    logging.info("Initializing camera")
    camera = CameraClass(*DATA["args"], **DATA["kwargs"])

    # Initalize the camera iterator
    # so the result is always frame_idx, (t, frame)
    if camera.__class__.__name__ == "FSLVirtualCamera":
        camera_iterator = camera
    else:
        camera_iterator = enumerate(camera)

    windows = []

    metadata = pd.read_csv(METADATA)
    metadata = metadata[TimeWindow._required_metadata]

    for i, row in metadata.iterrows():
        print(FPS)
        print(row)

        time_window = TimeWindow(
            i+1, **row,
            framerate=FPS, result_dir=OUTPUT, input_video=INPUT,
            all_frames=ALL, annotate=ARGS["annotate"], informative=ARGS["informative"]
        )
        windows.append(time_window)


    xyshape_pad = (
        max([window.xyshape[0] for window in windows]),
        max([window.xyshape[1] for window in windows])
    )

    print(xyshape_pad)

    for window in windows:
        window.xyshape_pad = xyshape_pad




    # Make sure windows are sorted by region_id and start
    windows_list = sorted(windows, key=lambda x: (x._region_id, x.start))

    # Make sure windows don't overlap
    # dont check the last window.., it cannot overlap with the next
    # since they are sorted, checking consecutive pairs is enough
    for idx in range(len(windows_list) - 1):
        try:
            window_is_before_next = windows_list[idx].end <= windows_list[idx+1].start
            windows_belong_to_different_rois = windows_list[idx]._region_id < windows_list[idx + 1]._region_id
            assert window_is_before_next or windows_belong_to_different_rois

        except AssertionError:
            # 1-based index for users
            logging.warning(windows_list[idx])
            logging.warning(windows_list[idx+1])
            logging.warning(window_is_before_next)
            logging.warning(window_is_before_next)
            logging.warning(windows_list[idx].end)
            logging.warning(windows_list[idx+1].start)
            print(windows_list[(idx-5):(idx+5)])
            logging.warning(windows_belong_to_different_rois)
            message = "Window %d overlaps with window %d. Make sure they don't!" % (idx+1, idx+2)
            raise Exception(message)


    try:
        for window in windows_list:
            window.open(camera)
            window.run()
            window.close()

    except Exception as error:
        logging.error("Error running your windows. Check details below")
        logging.error(error)
        logging.error(traceback.print_exc())
    finally:
        camera._close()




if __name__ == "__main__":

    # Declare an argument parser for the user to provide input
    parser = argparse.ArgumentParser(description="Sample video fragments from a .mp4 video generated in an ethoscope. Windows are defined in an external .csv file.")
    parser.add_argument("--input", type=str, required=True, help="Path to .mp4 file produced via offline analysis using the provided class.")
    parser.add_argument("--output", type=str, help="Path to folder where fragments will be stored. Created on the spot if it does not exist.")
    parser.add_argument("-c", "--camera", help="Name of camera class", default="MovieVirtualCamera", type=str, choices=["FSLVirtualCamera", "MovieVirtualCamera"])
    parser.add_argument(
        "--metadata", type=str,
        help="Path to .csv of two columns representing first and last timepoint in each sample (s),\
            referenced to the start of the video."
    )

    parser.add_argument("-a", "--all", dest="all", action="store_true", default=False, help="If True, all frames are inluded, otherwise only those that have a match in the corresponding dbfile.")
    parser.add_argument("--annotate", dest="annotate", action="store_true", default=False, help="Whether to mark the ROI number and the fly position or not.")
    parser.add_argument("-f", "--framerate", type=int, required=True, help="Framerate of the output videos.")
    parser.add_argument("--informative", dest="informative", action="store_true", default=False, help="Whether to prepend the max_velocity to the filename or not.")

    ARGS = vars(parser.parse_args())
    main(ARGS)
