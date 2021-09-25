from .cameras import OurPiCameraAsync, PiFrameGrabber

class HRPiFrameGrabber(PiFrameGrabber):
    _VIDEO_PORT = False


class HRPiCameraAsync(OurPiCameraAsync):
    _frame_grabber_class = HRPiFrameGrabber
    _description = {"overview": "A class that uses the HRPiFrameGrabber to exploit the increased resolution in the RPi HQ camera",
                    "arguments": []}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, target_resolution = (4056, 3040), **kwargs)



