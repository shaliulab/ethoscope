import datetime
import numpy as np

from .cameras import OurPiCameraAsync, PiFrameGrabber

class HRPiFrameGrabber(PiFrameGrabber):
    _VIDEO_PORT = False


class HRPiCameraAsync(OurPiCameraAsync):
    _frame_grabber_class = HRPiFrameGrabber
    _description = {"overview": "A class that uses the HRPiFrameGrabber to exploit the increased resolution in the RPi HQ camera",
                    "arguments": []}

    def __init__(self, *args, store=True, **kwargs):
        super().__init__(*args, target_resolution = (4056, 3040), **kwargs)
        
        if store:
            
            import imgstore
            from ethoscope.web_utils.helpers import get_machine_id, get_machine_name
            
            machine_id = get_machine_id()
            machine_name = get_machine_name()
            framerate = kwargs.get("framerate", 25)
            resolution = self._resolution
            chunk_duration = 300
            videos_dir = f"/ethoscope_data/results/{machine_id}/{machine_name}"
            kwargs = {
                  "mode": 'w',
                  "isColor": False,
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
            if self._store:
                imgstore.add_image(img, self._frame_idx, t)

            return t, img

        def _close(self):
            result = super()._close()
            imgstore.close()
            return result




