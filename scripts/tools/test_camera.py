
def benchmark_camera(target_fps, target_resolution, awb_gains, awb_mode, shutter_speed, iso): 

    attrs = ['t','analog_gain', 'digital_gain', 'exposure_speed', 'shutter_speed', 'iso', 'framerate', 'resolution', 'awb_gains']
    i = 0
    j = 0
    t0 = time.time()
    row = [None] * len(attrs)

    # Test camera settings and relation between them
    preview_length = 100
    live_data = {attr: np.array([None,]*preview_length) for attr in attrs}
    filename = f'camera_stats_@{target_fps}fps_{args["resolution"]}_{shutter_speed}shutter_{iso}iso_{args["awb_gains"]}awb.txt'
    file_path = os.path.join('/root', filename)

    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass


    with open(file_path, 'a+') as fh:
        fh.write('t,analog_gain,digital_gain,exposure_speed,shutter_speed,iso,framerate,width,height,red,blue\n')
    
        with picamera.PiCamera() as camera:
        
            camera.framerate = target_fps
            camera.resolution = target_resolution
            camera.awb_mode = awb_mode
            if awb_mode == 'off':
                camera.awb_gains = awb_gains
    
            if exposure_mode == 'off':
                #logger.info(f'Camera exposure mode by default" {camera.exposure_mode}')
                camera.shutter_speed = shutter_speed
                camera.exposure_mode = 'off'
    
            raw_camera = PiRGBArray(camera, size = target_resolution)
    
            for frame in camera.capture_continuous(raw_camera, format='bgr', use_video_port=True):
                try:
                    raw_camera.truncate(0)
                    t = time.time() - t0
                    #logger.info(f't elapsed: {t}')
    
                    attr_idx = 0 
                    for attr in attrs:
                        if attr_idx == 0:
                            row[0] = str(t)
                            attr_idx += 1
                            continue
    
                        try:
                            value = float(getattr(camera, attr, None))
                        except TypeError:
                            value = getattr(camera, attr, None)
            
                        #print(f'{attr}: {value}')
                        live_data[attr][j] = value
                            #live_data[attr].pop(0)
                            #live_data[attr].append(value)
                            #live_data[attr] = np.array(live_data[attr][1:], value)
        
                        if not attr in ['awb_gains', 'resolution']:
                            row[attr_idx] = str(float(value))
                        elif attr == 'awb_gains':
                            red_gain = str(float(value[0].numerator / value[0].denominator))
                            blue_gain = str(float(value[1].numerator / value[1].denominator))
                            row[attr_idx] = ','.join([red_gain, blue_gain]) 
        
                        elif attr == 'resolution':
                            width = str(float(value[0]))
                            height = str(float(value[1]))
                            row[attr_idx] = ','.join([width, height]) 
    
                        attr_idx += 1
                    # end for loop of attrs
        
                    #logger.info(row)
                    fh.write(','.join(row) + '\n')
                except IndexError:
                    logger.error('Error')
                    break
    
    
                    #live_data[attr].plot()
                    #plt.savefig(f'/tmp/{attr}.png')
        
                    #logging.warning(f'{attr}: {value}')
        
                #try:
                #    raw_camera.truncate(0)
                #    out = frame.array
                #    #cv2.imwrite(f'/tmp/last_img_{i}.png', out)
                #    if i == 3:
                #        i = 0
                #    else:
                #        i += 1
                #    j += 1
        
        
                #except Exception as e:
                #    break
    
    
    
            # end for loop
    
if __name__ == "__main__":

    import picamera
    from picamera.array import PiRGBArray
    import logging
    import cv2
    import time
    import numpy as np
    import os
    import os.path
    import argparse
    import sys
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    
    ap = argparse.ArgumentParser()
    
    ap.add_argument('-f', '--framerate', type = int, default=10)
    ap.add_argument('-r', '--resolution', type = str, default='1280x960')
    ap.add_argument('-s', '--shutter_speed', type = int, default=None)
    ap.add_argument('-i', '--iso', type = int, default=0)
    ap.add_argument('-a', '--awb_gains', type = str, default=None)
    args = vars(ap.parse_args())
    
    logger.info(args)

    target_fps = args['framerate']
    target_resolution= [int(e) for e in args['resolution'].split('x')]
    shutter_speed = args['shutter_speed']
    iso = args['iso']
    if args['awb_gains'] is None:
        awb_mode = 'auto'
        awb_gains = None
    
    else:
        awb_mode = 'off'
        awb_gains = (float(e) for e in args['awb_gains'].split(','))
    
    if args['shutter_speed'] is None:
        exposure_mode = 'auto'
    else:
        exposure_mode = 'off'

    benchmark_camera(target_fps, target_resolution, awb_gains, awb_mode, shutter_speed, iso)

