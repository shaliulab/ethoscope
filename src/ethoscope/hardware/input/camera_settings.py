import logging
logging.basicConfig(level=logging.INFO)


def report_camera(camera):
    logging.info(f'camera framerate: {camera.framerate}')
    logging.info(f'camera resolution: {camera.resolution}')
    logging.info(f'camera exposure_mode: {camera.exposure_mode}')
    logging.info(f'camera shutter_speed: {camera.shutter_speed}')
    logging.info(f'camera exposure_speed: {camera.exposure_speed}')
    logging.info(f'camera awb_gains: {camera.awb_gains}')
    logging.info(f'camera analog_gain: {float(camera.analog_gain)}')
    logging.info(f'camera digital_gain: {float(camera.digital_gain)}')
    logging.info(f'camera iso: {float(camera.iso)}')

def configure_camera(camera, mode, resolution=None, fps=None):

    # Lazy load dependencies
    import picamera
    import time
    from picamera_attributes import variables

    #ps = variables.ParameterSet({"awb_mode": "off", "awb_gains": (0.5,0.5), "exposure_mode": "off", "shutter_speed": 70000, "analog_gain": 1, "color_effects": (128, 128)})

    ps_target_detection = variables.ParameterSet({"awb_mode": "off", "awb_gains": (1.8,1.5), "exposure_mode": "off", "shutter_speed": 300000, "analog_gain": 8, "digital_gain": 2, "color_effects": (128, 128)})
    ps_target_detection.validate()
    ps_target_detection.cross_verify()

    ps_roi_builder = variables.ParameterSet({"contrast": 70, "awb_mode": "off", "awb_gains": (5,5), "exposure_mode": "off", "shutter_speed": 60000, "analog_gain": 1, "digital_gain": 1})
    ps_roi_builder.validate()
    ps_roi_builder.cross_verify()


    ps_tracker = variables.ParameterSet({"awb_mode": "off", "awb_gains": (.5, .5), "exposure_mode": "off", "shutter_speed": 70000, "analog_gain": 2.5, "digital_gain": 1, "color_effects": (128, 128)})
    ps_tracker.validate()
    ps_tracker.cross_verify()


    sets = {"tracker": ps_tracker, "target_detection": ps_target_detection, "roi_builder": ps_roi_builder}


    if resolution is not None:
        camera.resolution = resolution
    if fps is not None:
        camera.framerate = fps
    
    logging.info(f"Setting camera up for mode {mode}")
    camera, atts = sets[mode].update_cam(camera)

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

