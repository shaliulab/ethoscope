import time
import picamera

def main():
    with picamera.PiCamera(resolution=(1280, 960), framerate=20) as capture:
        capture.start_preview()
        time.sleep(2)
        capture.capture("img0001.jpg")
        capture.stop_preview()

main()
