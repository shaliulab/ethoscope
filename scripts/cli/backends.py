import time
import logging
import datetime

import numpy as np
import cv2


logging.basicConfig(level=logging.INFO)


def opencv_backend(
        stream, i, frame, resolution=None, framerate=None,
        start_time=None, duration=None, video_writer=None,
        chunk_count=None, chunk_duration=None, frame_count=None
    ):

    if (time.time() - start_time) < duration:

        stream.seek(0)
        stream.truncate()
        out = cv2.cvtColor(frame.array, cv2.COLOR_BGR2GRAY)

        # init the video writer if it's not yet
        if video_writer is None:

            start_chunk = time.time()
            video_writer = cv2.VideoWriter(
                    f"/root/video_{str(chunk_count).zfill(6)}.avi",
                    cv2.VideoWriter_fourcc(*"DIVX"),
                    framerate,
                    out.shape[::-1],
                    isColor=False
                    )

        # write the frame!
        video_writer.write(out)
        logging.info("Saving image")

        # if the chunk is already long enough
        # stop it and start a new one
        if (time.time() - start_chunk) > chunk_duration:
            video_writer.release()
            chunk_count += 1
            logging.info("Starting chunk")
            video_writer = cv2.VideoWriter(
                    f"/root/video_{str(chunk_count).zfill(6)}.avi",
                    cv2.VideoWriter_fourcc(*"DIVX"),
                    framerate,
                    out.shape[::-1],
                    isColor=False
                    )
            start_chunk = time.time()

        return True

    else:
        video_writer.release()
        return False


def imgstore_backend(
        stream, i, frame, resolution=None, framerate=None,
        start_time=None, duration=None, video_writer=None,
        chunk_count=None, chunk_duration=None, frame_count=None
    ):

    import imgstore

    path = f"/root/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}/"

    if (time.time() - start_time) < duration:

        stream.seek(0)
        stream.truncate()
        out = cv2.cvtColor(frame.array, cv2.COLOR_BGR2GRAY)

        # init the video writer if it's not yet
        if video_writer is None:

            start_chunk = time.time()
            kwargs = {
                  "mode": 'w',
                  "framerate": framerate,
                  "basedir": path,
                  "imgshape": resolution[::-1], # reverse order so it becomes nrows x ncols i.e. height x width
                  "imgdtype": np.uint8,
                  "chunksize": framerate * chunk_duration # I want my videos to contain 5 minutes of data (300 seconds)
            }

            video_writer = imgstore.new_for_format(fmt="mjpeg/avi", **kwargs)

        video_writer.add_image(out, frame_count, time.time() - start_time)
        return True

    else:
        video_writer.release()
        return False

