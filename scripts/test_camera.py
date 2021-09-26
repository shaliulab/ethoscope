import picamera
import picamera.array
import cv2
import time
import logging
import argparse
import datetime
logging.basicConfig(level=logging.INFO)


def get_parser():

    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["opencv", "imgstore"], default="opencv")
    return ap


framerate = 0.25
video_writer = None

start_time = time.time()
duration = 3600 * 24
chunk_duration = 300
chunk_count = 0

def capture_video():
    resolution = (1280, 960)
    return capture_continuous(resolution, backend=opencv_backend, video_port=True)

def capture_img():
    resolution = (4056, 3040)
    return capture_continuous(resolution, backend=opencv_backend, video_port=False, shutter_speed=2000, exposure_mode="off", awb_mode="off", awb_gains=(1.8, 1.5))

def capture_continuous(resolution, backend, video_port=True, **kwargs):
    """
    The RPi HQ camera cannot capture better resolution than 1280x960
    when recording a video
    """
    global framerate



    shutter_speed = kwargs.pop("shutter_speed")
    exposure_mode = kwargs.pop("exposure_mode")
    awb_mode = kwargs.pop("awb_mode")
    awb_gains = kwargs.pop("awb_gains")

    
    with picamera.PiCamera(resolution=resolution, framerate=framerate, **kwargs) as camera:
        camera.awb_mode = "off"
        camera.awb_gains = (1.8, 1.5)
        camera.annotate_text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        camera.exposure_mode = exposure_mode 
        camera.shutter_speed = shutter_speed
        camera.awb_mode = awb_mode
        camera.awb_gains = awb_gains
    
        stream = picamera.array.PiRGBArray(camera, size=resolution)
    
        for i, frame in enumerate(camera.capture_continuous(stream, format="bgr", use_video_port=video_port)):

            backend(stream, i, frame, resolution=resolution)



    return 0



def opencv_backend(stream, i, frame, resolution=None):


    global start_time
    global duration
    global framerate
    global video_writer
    global chunk_count
    global chunk_duration

    if (time.time() - start_time) < duration:

        stream.seek(0)
        stream.truncate()
        out = cv2.cvtColor(frame.array, cv2.COLOR_BGR2GRAY)

        # init the video writer if it's not yet
        if video_writer is None:

            start_chunk = time.time()
            video_writer = cv2.VideoWriter(
                    f"/root/video_{str(chunk_count).zfill(6)}.avi",
                    cv2.VideoWriter_fourcc(*"DIVX"),
                    framerate,
                    out.shape[::-1],
                    isColor=False
                    )

        # write the frame!
        video_writer.write(out)
        logging.info("Saving image")

        # if the chunk is already long enough
        # stop it and start a new one
        if (time.time() - start_chunk) > chunk_duration:
            video_writer.release()
            chunk_count += 1
            video_writer = cv2.VideoWriter(
                    f"/root/video_{str(chunk_count).zfill(6)}.avi",
                    cv2.VideoWriter_fourcc(*"DIVX"),
                    framerate,
                    out.shape[::-1],
                    isColor=False
                    )
            start_chunk = time.time()

    else:
        video_writer.release()



def capture_imgstore():
    resolution = (4056, 3040)
    return capture_continuous(resolution, backend=imgstore_backend, video_port=False, shutter_speed=2000, exposure_mode="off", awb_mode="off", awb_gains=(1.8, 1.5))

def imgstore_backend(stream, i, frame, resolution):

    global start_time
    global duration
    global framerate
    global video_writer
    global chunk_count
    global chunk_duration
    path = f"/root/{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",

    if (time.time() - start_time) < duration:

        stream.seek(0)
        stream.truncate()
        out = cv2.cvtColor(frame.array, cv2.COLOR_BGR2GRAY)

        # init the video writer if it's not yet
        if video_writer is None:

            start_chunk = time.time()
            kwargs = {"framerate": framerate,
                  "mode": 'w',
                  "basedir": path,
                  "imgshape": resolution[::-1], # reverse order so it becomes nrows x ncols i.e. height x width
                  "imgdtype": np.uint8,
                  "chunksize": framerate * chunk_duration # I want my videos to contain 5 minutes of data (300 seconds)
            }


            video_writer = imgstore.new_for_format(fmt="h264/avi", **kwargs)

    else:
        video_writer.release()


    
def main():
    ap = get_parser()
    args = ap.parse_args()

    if args.backend == "opencv":
        capture_img()
    elif args.backend == "imgstore":
        capture_imgstore()
    else:
        raise Exception("Invalid backend")


if __name__ == "__main__":
    main()
