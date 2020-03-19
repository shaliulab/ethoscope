import subprocess
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


fps_list = [10, 5, 1, 2, 3, 4]
shutter_speed_list = list(range(10000, 100000, 10000))
awb_gains_list = [(1.8, 1.5), None]
#analog_gains_list = [5,6,7]



for framerate in fps_list:
    for shutter_speed in shutter_speed_list:
        for awb_gains in awb_gains_list:
            #for analog_gains in analog_gains_list:
            cmd = f"python benchmark_camera.py --framerate {framerate} --shutter_speed {shutter_speed}"
            if not awb_gains is None:
                cmd = cmd + f" --awb_gains {','.join([str(e) for e in awb_gains])}"
            logger.warning(f"Running {cmd}")
            cmd_list = cmd.split(" ")
            subprocess.run(cmd_list)
