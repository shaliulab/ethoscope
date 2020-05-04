import picamera
import time
from picamera_attributes import variables
ps = variables.ParameterSet({"awb_mode": "off", "awb_gains": (0.5,0.5), "exposure_mode": "off", "shutter_speed": 70000, "analog_gain": 1, "iso": 100, "color_effects": (128, 128)})
ps.validate()
ps.cross_verify()

def configure_camera(camera, resolution=None, fps=None):
    if resolution is not None:
        camera.resolution = resolution
    if fps is not None:
        camera.framerate = fps

    camera, atts = ps.update_cam(camera)

    #camera.color_effects = (128,128)
    #camera.awb_mode = "off"
    #time.sleep(1)
    #camera.awb_gains = (1.8, 1.5)
    #camera.exposure_mode = "off"
    #time.sleep(3)
    #camera.shutter_speed = 80000
    #time.sleep(1)
    ## give time for the analog and digital gain to adjust
    ## for the new shutter speed
    #camera.exposure_mode = "auto"
    #time.sleep(4)
    #camera.exposure_mode = "off"


    return camera

