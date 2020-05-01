"""
A script to exctract frames from a .db file and create a video.
There are to external deps: ffmpeg and imagemagick.
"""
import sqlite3
import io
import tempfile
import shutil
import os
from argparse import ArgumentParser 
import datetime
import glob
import numpy as np
import cv2
import logging
logging.basicConfig(level=logging.INFO)



def annotate_image(args):
    input_file, time, t0 = args
    label = datetime.datetime.fromtimestamp(time/1000 + t0).strftime('%Y-%m-%d %H:%M:%S')

    im = cv2.imread(input_file)
    mean_itensity = np.mean(im)
    logging.info(f"File {input_file}")
    logging.info(f"Mean intensity is {mean_itensity}")

    command = "convert %s -pointsize 50  -font FreeMono -background Khaki  label:'%s' +swap -gravity Center -append %s" % (input_file, label, input_file)
    os.system(command)

def get_mean_intensity(file, annotate=True):

    file_name = tempfile.NamedTemporaryFile(prefix="last_frame", suffix = ".png", delete=False).name
    with sqlite3.connect(file, check_same_thread=False) as conn:
        cursor = conn.cursor()
        sql_metadata = 'select * from METADATA'
        conn.commit()
        cursor.execute(sql_metadata)
        t0 = 0
        for field, value in cursor:
            if field == "date_time":
                t0 = float(value)

        sql1 = 'select id,t,img from IMG_SNAPSHOTS ORDER BY t DESC LIMIT 1'
        conn.commit()
        cursor.execute(sql1)



        for i,c in enumerate(cursor):
            id, t, blob = c
            file_like = io.BytesIO(blob)
            out_file = open(file_name, "wb")
            file_like.seek(0)
            shutil.copyfileobj(file_like, out_file)

        args = (file_name,t,t0)
        annotate_image(args)



if __name__ == '__main__':

    ETHOGRAM_DIR = "/ethoscope_data/results"
    MACHINE_ID_FILE = '/etc/machine-id'
    MACHINE_NAME_FILE = '/etc/machine-name'

    parser = ArgumentParser()
    parser.add_argument("-i", "--input", dest="input", help="The input .db file")
    parser.add_argument("-a", "--annotate", dest="annot", default=False, help="Whether date and time should be written on the bottom of the frames", action="store_true")

    args = vars(parser.parse_args())

    get_mean_intensity(args["input"],
                       args["annot"]
                      )
