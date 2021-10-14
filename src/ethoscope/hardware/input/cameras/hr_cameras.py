import datetime
import numpy as np
import logging
import traceback
import time

import cv2

from .cameras import OurPiCameraAsync, PiFrameGrabber

class HRPiFrameGrabber(PiFrameGrabber):
    _VIDEO_PORT = False


class JetsonNanoFrameGrabber(PiFrameGrabber):

    @staticmethod
    def gstreamer_pipeline(
        capture_width=1280,
        capture_height=720,
        display_width=1280,
        display_height=720,
        framerate=60,
        flip_method=0,
    ):
        return (
            "nvarguscamerasrc ! "
            "video/x-raw(memory:NVMM), "
            "width=(int)%d, height=(int)%d, "
            "format=(string)NV12, framerate=(fraction)%d/1 ! "
            "nvvidconv flip-method=%d ! "
            "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
            "videoconvert ! "
            "video/x-raw, format=(string)BGR ! appsink"
            % (
                capture_width,
                capture_height,
                framerate,
                flip_method,
                display_width,
                display_height,
            )
        )
        
    def run(self):
        """
        Initialise pi camera, get frames, convert them fo greyscale, and make them available in a queue.
        Run stops if the _stop_queue is not empty.
        """

        try:

            pipeline = self.gstreamer_pipeline(flip_method=0, capture_width=self._target_resolution[0], capture_height=self._target_resolution[1], framerate=self._target_fps)
            logging.warning(pipeline)

            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if cap.isOpened():
                ret_val = True
                while ret_val:
                    ret_val, img = cap.read()
                    out = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    self._queue.put(out)

                    if not self._stop_queue.empty():
                        logging.info("The stop queue is not empty. This signals it is time to stop acquiring frames")
                        self._stop_queue.get()
                        self._stop_queue.task_done()
                        break
            
                cap.release()
    
        except Exception as error:
            logging.error(error)
            logging.error(traceback.print_exc())
            logging.warning("Some problem acquiring frames from the camera")

        finally:
            self._queue.task_done() # this tell the parent the thread can be closed
            logging.warning("Camera Frame grabber stopped acquisition cleanly")




class JetsonNanoCamera(OurPiCameraAsync):
    _frame_grabber_class = JetsonNanoFrameGrabber


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
                  "chunksize": int(framerate * chunk_duration) # I want my videos to contain 5 minutes of data (300 seconds)
            }

            logging.warning(f"Chunksize: {kwargs['chunksize']}")
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




