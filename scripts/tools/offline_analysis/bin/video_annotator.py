#! /home/vibflysleep/anaconda3/envs/ethoscope_annotation/bin/python
# -*- coding: utf-8 -*-


import argparse
import logging
from muvilab.annotator import Annotator

r"""
This example downloads a youtube video from the Olympic games, splits it into
several clips and let you annotate it
"""


logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser("Launch MuViLab")
parser.add_argument("--input", type=str,required=True)
parser.add_argument("--nshow", type=int, default=20)
parser.add_argument("--shuffle", action="store_true", dest="shuffle", default=False)
ARGS = vars(parser.parse_args())
NSHOW = ARGS["nshow"]
SHUFFLE = ARGS["shuffle"]


# Set up some folders
clips_folder = ARGS["input"]
annotation_file = '%s_labels.json' % clips_folder.strip("/")
logging.info("Saving labels to %s", annotation_file)


# Initialise the annotator
annotator = Annotator([
        {'name': 'low', 'color': (255, 0, 0)},
        {'name': 'medium', 'color': (0, 0, 255)},
        {'name': 'high', 'color': (0, 255, 0)},
        {'name': 'feeding', 'color': (0, 255, 255)},
        {'name': 'hidden', 'color': (255, 255, 255)},
        ],
        clips_folder, sort_files_list=True, N_show_approx=NSHOW, screen_ratio=16/9,
        image_resize=1, loop_duration=None, annotation_file=annotation_file)

# Run the annotator
annotator.main(SHUFFLE)
