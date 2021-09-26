import datetime
import numpy as np
import logging

import cv2

from .cameras import OurPiCameraAsync, PiFrameGrabber

class HRPiFrameGrabber(PiFrameGrabber):
    _VIDEO_PORT = False


class HRPiCameraAsync(OurPiCameraAsync):
    _frame_grabber_class = HRPiFrameGrabber
    _description = {"overview": "A class that uses the HRPiFrameGrabber to exploit the increased resolution in the RPi HQ camera",
                    "arguments": []}

    def __init__(self, *args, store=True, **kwargs):
        super().__init__(*args, target_resolution = (4056, 3040), **kwargs)
        
        if isinstance(store, str):

            if store == "True":
                store = True
            elif store == "False":
                store = False
            else:
                raise Exception("Invalid value of store")

        if store:
            
            import imgstore
            from ethoscope.web_utils.helpers import get_machine_id, get_machine_name
            
            machine_id = get_machine_id()
            machine_name = get_machine_name()
            framerate = self._framerate
            resolution = self._resolution
            chunk_duration = 300
            videos_dir = f"/ethoscope_data/results/{machine_id}/{machine_name}"
            kwargs = {
                  "mode": 'w',
                  "isColor": True,
                  "framerate": framerate,
                  "basedir": f"{videos_dir}/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}",
                  "imgshape": resolution[::-1], # reverse order so it becomes nrows x ncols i.e. height x width
                  "imgdtype": np.uint8,
                  "chunksize": framerate * chunk_duration # I want my videos to contain 5 minutes of data (300 seconds)
            }


            self._store = imgstore.new_for_format(fmt="mjpeg/avi", **kwargs)
        else:
            self._store = None

    def _next_time_image(self):
        t, img = super()._next_time_image()

        logging.warning("next_time_image of HR")
        logging.warning(img.shape)
        logging.warning(self._resolution)
        logging.warning(self._framerate)


        if not self._store is None:
            logging.warning("Writing image")
            self._store.add_image(img, self._frame_idx, t)
            #self._store.add_image(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), self._frame_idx, t)

        return t, img

    def _close(self):
        result = super()._close()
        imgstore.close()
        return result




