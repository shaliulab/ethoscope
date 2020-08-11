import picamera
from picamera.array import PiRGBArray
from picamera.exc import PiCameraMMALError
import cv2
target_framerate = 2
target_resolution = (1280, 960)

# 0 Initialize the camera object in Python
# i.e. generate a camera handler
print("Initialize camera")
try:
    with picamera.PiCamera(framerate=target_framerate, resolution=target_resolution) as capture:
        # 1 Start preview i.e. turn on the camera
    
        print("start preview")
        capture.start_preview()
        # 2 Initialize a PRGBArray object that will store the output of the camera
        # https://picamera.readthedocs.io/en/release-1.10/api_array.html#pirgbarray
        print("raw capture")
        raw_capture = PiRGBArray(capture, size=target_resolution)
    
        # 3 Start captuting the frames in Python
        for frame in capture.capture_continuous(raw_capture, format="bgr", use_video_port=True):
    
            # 3.1 Truncate
            print("Truncate")
            raw_capture.truncate(0)
            # 3.2 Extract and make gray 
            print("Extract and make gray")
            out = cv2.cvtColor(frame.array,cv2.COLOR_BGR2GRAY)
            print(out)
    
        print("Closing")
except picamera.exc.PiCameraMMALError as error:
    print(error)
