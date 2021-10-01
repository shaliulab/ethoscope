from os import path
# from threading import Thread
import traceback
import logging
logging.basicConfig(level=logging.INFO)
import time
from ethoscope.web_utils.control_thread import ControlThread, ExperimentalInformation
from ethoscope.hardware.input.cameras.camera_settings import configure_camera, report_camera
from ethoscope.utils.description import DescribedObject
from ethoscope.utils.debug import EthoscopeException

import os
import tempfile
import shutil
import multiprocessing
import glob
import datetime
import time
import subprocess
import cv2
import pickle
import os.path

#For streaming
from http.server import BaseHTTPRequestHandler, HTTPServer
import io

class CamStreamHTTPServer(HTTPServer):
    '''
    A custom inheritance of HTTPServer
    This is needed to avoid using camera in the global space
    Adapted from: https://mail.python.org/pipermail/python-list/2012-March/621727.html
    '''
    
    def __init__(self, camera, *args, **kw):
        self.camera = camera
        HTTPServer.__init__(self, *args, **kw)


class CamHandler(BaseHTTPRequestHandler):
    '''
    The Handler to the Camera Stream interrogates the camera when it runs
    '''
    def do_GET(self):
        if self.path.endswith('.mjpg'):
            self.send_response(200)
            self.send_header('Content-type','multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            stream=io.BytesIO()
            try:
              start=time.time()
              for i, foo in enumerate(self.server.camera.capture_continuous(stream,'jpeg',use_video_port=True)):
                if i == 5:
                    self.server.camera = configure_camera(self.server.camera, mode = "roi_builder")
                    time.sleep(5)
                if i == 10:
                    self.server.camera = configure_camera(self.server.camera, mode = "tracker")
                    time.sleep(5)

                self.wfile.write(b"--jpgboundary")
                self.send_header('Content-type','image/jpeg')
                self.send_header('Content-length',len(stream.getvalue()))
                self.end_headers()
                self.wfile.write(stream.getvalue())
                stream.seek(0)
                stream.truncate()
                time.sleep(.1)

            except KeyboardInterrupt:
                pass
            return
        else:
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write("""<html><head></head><body>
              <img src="/cam.mjpg"/>
            </body></html>""")
            return
  
class PiCameraProcess(multiprocessing.Process):
    '''
    This opens a PiCamera process for recording or streaming video
    For recording, files are saved in chunks of time duration
    In principle, the two activities couldbe done simultaneously ( see https://picamera.readthedocs.io/en/release-1.12/recipes2.html#capturing-images-whilst-recording )
    but for now they are handled independently
    '''
        
    _VIDEO_CHUNCK_DURATION = 30 * 10
    def __init__(self, stop_queue, video_prefix, video_root_dir, img_path, width, height, fps, bitrate, stream=False):
        self._stop_queue = stop_queue
        self._img_path = img_path
        self._resolution = (width, height)
        self._fps = fps
        self._bitrate = bitrate
        self._video_prefix = video_prefix
        self._video_root_dir = video_root_dir
        self._stream = stream
        super(PiCameraProcess, self).__init__()

    def _make_video_name(self, i):
        w,h = self._resolution
        video_info= "%ix%i@%i" %(w, h, self._fps)
        return '%s_%s_%05d.h264' % (self._video_prefix, video_info, i)
        
    # def _write_video_index(self):
    #     index_file = os.path.join(self._video_root_dir, "index.html")
    #     all_video_files = [y for x in os.walk(self._video_root_dir) for y in glob.glob(os.path.join(x[0], '*.h264'))]
    #
    #     with open(index_file, "w") as index:
    #         for f in all_video_files:
    #             index.write(f + "\n")

    def find_target_coordinates(self, camera):

        logging.info("Checking targets in resulting video are visible and video is suitable for offline analysis")
        
        # to analyzs the same frames offline
        from ethoscope.hardware.input.cameras import MovieVirtualCamera
        from ethoscope.roi_builders.target_roi_builder import FSLSleepMonitorWithTargetROIBuilder
        from ethoscope.drawers.drawers import DefaultDrawer
        from ethoscope.core.tracking_unit import TrackingUnit
        from ethoscope.trackers.adaptive_bg_tracker import AdaptiveBGModel as tracker_class

        i = 0
        try:
            # Log camera status and take shot
            target_detection_path = "/tmp/target_detection_{}.png"
            camera.framerate = 2
            time.sleep(1)
            camera = configure_camera(camera, mode = "target_detection")
            n = 0
            roi_builder = FSLSleepMonitorWithTargetROIBuilder()
            drawer = DefaultDrawer()

            target_coord_file = self._video_prefix + "targets.pickle"
            rois_file = self._video_prefix + "rois.pickle"
            failure = True
            

            while failure and n < 5:
                try:
                    camera = configure_camera(camera, mode = "target_detection")
                    report_camera(camera)
                    camera.capture(target_detection_path.format(n))
                    time.sleep(1)
                    img = cv2.imread(target_detection_path.format(n))
                    rois = roi_builder.build(img)

                    logging.info("Annotating frame for human supervision")
                    unit_trackers = [TrackingUnit(tracker_class, r, None) for r in rois]
                    annotated = drawer.draw(img, tracking_units=unit_trackers, positions=None)
                    tmp_dir = os.path.dirname(self._img_path)
                    annotated_path = os.path.join(tmp_dir, "last_img_annotated.jpg")
                    logging.info(f"Saving annotated frame to {annotated_path}")
                    cv2.imwrite(annotated_path, annotated)

                    logging.info("Saving pickle files")
                    with open(target_coord_file, "wb") as fh:
                        pickle.dump(roi_builder._sorted_src_pts, fh)
                    with open(rois_file, "wb") as fh:
                        pickle.dump(rois, fh)
                    failure = False


                except Exception as e:
                    logging.info(e)
                    failure = True # not needed, but for readability
                    n += 1

            if failure:
                logging.info("Failure")
                raise EthoscopeException("I tried taking 5 shots and none is good! Check them at /tmp/target_detection_{i}.png")

            else:
                logging.info("Success")
                return True


        except Exception as e:
            logging.error("Error on starting video recording process:" + traceback.format_exc())

    def run(self):
        import picamera
        i = 0

        try:
            with picamera.PiCamera(resolution=self._resolution, framerate=self._fps) as camera:

                if not self._stream:
                    try:
                        validation = self.find_target_coordinates(camera)

                    except Exception as e:
                        logging.error("Sorry, the targets will not be visible in this video. Try again!")
                        raise e

                # put the camera in tracker mode
                # this mode is defined by the camera_settings module
                camera.framerate = self._fps
                time.sleep(2)
                camera = configure_camera(camera, mode="tracker")         
                time.sleep(2)

                # doing a video recording
                if not self._stream:
                    output = self._make_video_name(i)
                    camera.start_recording(output, bitrate=self._bitrate)
                    
                # self._write_video_index()
                start_time = time.time()
                
                # doing a stream
                if self._stream:
                    try:
                        self.server = CamStreamHTTPServer(camera, ('', 8008), CamHandler)
                        self.server.serve_forever()

                    finally:
                        self.server.shutdown()
                        camera.close()

                # continue the video recording
                else:
                    i += 1
                    while True:
                        camera.wait_recording(2)
                        camera = configure_camera(camera, mode = "tracker")
                        report_camera(camera)
                        camera.capture(self._img_path, use_video_port=True, quality=50)
    
                        if time.time() - start_time >= self._VIDEO_CHUNCK_DURATION:
                            camera.split_recording(self._make_video_name(i))
                            # self._write_video_index()
                            start_time = time.time()
                            i += 1
                        if not self._stop_queue.empty():
                            self._stop_queue.get()
                            self._stop_queue.task_done()
                            break

                camera.wait_recording(1)
                camera.stop_recording()

        except Exception as e:
            logging.error("Error on starting video recording process:" + traceback.format_exc())


class RobustGeneralVideoRecorder(DescribedObject):
    _description  = {  "overview": "A video simple recorder",
                            "arguments": [
                                {"type": "number", "name":"width", "description": "The width of the frame","default":1280, "min":480, "max":1980,"step":1},
                                {"type": "number", "name":"height", "description": "The height of the frame","default":960, "min":360, "max":1080,"step":1},
                                {"type": "number", "name":"fps", "description": "The target number of frames per seconds","default":25, "min":1, "max":25,"step":1},
                                {"type": "number", "name":"bitrate", "description": "The target bitrate","default":200000, "min":0, "max":10000000,"step":1000}
                               ]}

    def __init__(self, video_prefix, video_dir, img_path,width=1280, height=960,fps=12,bitrate=200000,stream=False):

        self._stop_queue = multiprocessing.JoinableQueue(maxsize=1)
        self._stream = stream
        self._p = PiCameraProcess(self._stop_queue, video_prefix, video_dir, img_path, width, height,fps, bitrate, stream)


    def run(self):
        self._is_recording = True
        self._p.start()
        while self._p.is_alive():
            time.sleep(.25)
            
    def stop(self):
        self._is_recording = False
        self._stop_queue.put(None)
        self._stop_queue.close()
        
        if self._stream:
            self._p.terminate()
        else:
            self._p.join(10)

class RobustVideoRecorder(RobustGeneralVideoRecorder):
    _description  = { "overview": """
    A preset 1280 x 960, 25fps, bitrate = 2e5 video recorder
    that builds ROIs and uses dual camera settings.
    """, "arguments": []}
    def __init__(self, video_prefix, video_dir, img_path):
        super(StandardVideoRecorder, self).__init__(video_prefix, video_dir, img_path,
                                        width=1280, height=960,fps=12,bitrate=500000)

