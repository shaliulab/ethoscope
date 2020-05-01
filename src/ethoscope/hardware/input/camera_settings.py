import picamera
import time

def configure_camera(camera, resolution, fps):
    camera.resolution = resolution
    camera.framerate = fps

    camera.color_effects = (128,128)
    camera.awb_mode = "off"
    time.sleep(1)
    camera.awb_gains = (1.8, 1.5)
    camera.exposure_mode = "off"
    time.sleep(3)
    camera.shutter_speed = 80000
    time.sleep(1)
    # give time for the analog and digital gain to adjust
    # for the new shutter speed
    camera.exposure_mode = "auto"
    time.sleep(4)
    camera.exposure_mode = "off"
    return camera

