__author__ = 'antonio'

import time
import logging
logging.basicConfig(level=logging.INFO)
import os
import traceback

try:
    from cv2.cv import CV_CAP_PROP_FRAME_WIDTH as CAP_PROP_FRAME_WIDTH
    from cv2.cv import CV_CAP_PROP_FRAME_HEIGHT as CAP_PROP_FRAME_HEIGHT
    from cv2.cv import CV_CAP_PROP_FRAME_COUNT as CAP_PROP_FRAME_COUNT
    from cv2.cv import CV_CAP_PROP_POS_MSEC as CAP_PROP_POS_MSEC
    from cv2.cv import CV_CAP_PROP_FPS as CAP_PROP_FPS

except ImportError:
    from cv2 import CAP_PROP_FRAME_WIDTH, CAP_PROP_FRAME_HEIGHT, CAP_PROP_FRAME_COUNT, CAP_PROP_POS_MSEC, CAP_PROP_FPS

import cv2
from ethoscope.utils.debug import EthoscopeException
import multiprocessing
import traceback
import queue

from .camera_settings import configure_camera
from .cameras import OurPiCameraAsync, PiFrameGrabber


class DualPiFrameGrabber(PiFrameGrabber):

    def __init__(self, exposure_queue, *args, **kwargs):
        """
        Class to grab frames from pi camera. Designed to be used within :class:`~ethoscope.hardware.camreras.camreras.OurPiCameraAsync`
        This allows to get frames asynchronously as acquisition is a bottleneck.
        Frames are grabbed with two settings, one for target detection during the first minute or so of the experiment
        and another one thereafter
        This optimizes image quality (minimal exposure time and iso) while making sure the flies are trackable
        and the targets are very well visible during the roi building step

        :param target_fps: desired fps
        :type target_fps: int
        :param target_resolution: the desired resolution (w, h)
        :type target_resolution: (int, int)
        :param queue: a queue that stores frame and makes them available to the parent process
        :type queue: :class:`~multiprocessing.JoinableQueue`
        :param stop_queue: a queue that can stop the async acquisition
        :type stop_queue: :class:`~multiprocessing.JoinableQueue`
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """

        self._exposure_queue = exposure_queue
        self._tracker_event = multiprocessing.Event()
        self._roi_builder_event = multiprocessing.Event()
        super().__init__(*args, **kwargs)

    @staticmethod
    def adjust_camera(camera, gain ,sign):
        # Lazy load dependencies
        import picamera
        import time
        from picamera_attributes import variables

        original_val = getattr(camera, gain)
        CameraParameter = variables.ParameterSet._supported[gain]

        if issubclass(CameraParameter, variables.Plural):

            val_change = (sign * 0.5, ) * CameraParameter._length

            val = [e1 + float(e2) for e1, e2 in zip(val_change, original_val)]
        else:
            val_change = sign * 0.5
            val = float(original_val) + val_change

        logging.info(f'Adjusting camera {gain} from {original_val} to {val}')
        cp = CameraParameter(val)
        cp.validate()
        camera = cp.update_cam(camera)
        return camera


    def run(self):
        """
        Initialise pi camera, get frames, convert them fo greyscale, and make them available in a queue.
        Run stops if the _stop_queue is not empty.
        """

        try:

            def capture_continuous(trials=0, recursion=0):
                # lazy import should only use those on devices
    
                # Warning: the following causes a major issue with Python 3.8.1
                # https://www.bountysource.com/issues/86094172-python-3-8-1-typeerror-vc_dispmanx_element_add-argtypes-item-9-in-_argtypes_-passes-a-union-by-value-which-is-unsupported
                from picamera.array import PiRGBArray
                from picamera import PiCamera
                from picamera.exc import PiCameraRuntimeError
                from picamera.exc import PiCameraValueError
    
                #with PiCamera(framerate=self._target_fps, resolution=self._target_resolution) as capture:
                with init_camera(framerate=self._target_fps, resolution=self._target_resolution) as capture:
                # wrap the call to picamera.PiCamera around a handler that
                # 1. creates a pidfile so the PID of the thread can be easily tracked
                # 2. removes a potential existing pidfile and kills the corresponding process
                # This is intended to avoid the Out of resources error caused by the camera thread not stopping upon monitor stop
                    logging.info(capture)
                    camera_info = capture.exif_tags
                    with open('/etc/picamera-version', 'w') as outfile:
                        print(camera_info, file=outfile)
    
                    capture.start_preview()
                    time.sleep(1)
                    capture = configure_camera(capture, mode = "target_detection")
                    time.sleep(5)
                    roi_builder_event = False
                    tracker_event = False
    
                    raw_capture = PiRGBArray(capture, size=self._target_resolution)
                    max_trials = 5

                    try:

                        for frame in capture.capture_continuous(raw_capture, format="bgr", use_video_port=True):

    
                            try:
                                gain, sign = self._exposure_queue.get(block=False)
                                capture = self.adjust_camera(capture, gain, sign)
                                logging.info('Success adjusting analog gain')
    
                            except queue.Empty:
                                pass
    
                            if self._roi_builder_event.is_set() and not roi_builder_event and recursion == 0:
                                capture = configure_camera(capture, mode="roi_builder")
                                roi_builder_event = True
                                logging.info('Success switching to roi_builder mode')
 
                            if self._tracker_event.is_set() and not tracker_event:
                                capture = configure_camera(capture, mode="tracker")
                                tracker_event = True
                                logging.info('Success switching to tracker mode')
    
                            if not self._stop_queue.empty():
                                logging.info(f"PID {os.getpid()}: The stop queue is not empty. Stop acquiring frames")
    
                                self._stop_queue.get()
                                self._stop_queue.task_done()
                                logging.warning("Stop Task Done")
                                break
    
                            logging.info(f'camera framerate: {capture.framerate}')
                            logging.info(f'camera resolution: {capture.resolution}')
                            logging.info(f'camera exposure_mode: {capture.exposure_mode}')
                            logging.info(f'camera shutter_speed: {capture.shutter_speed}')
                            logging.info(f'camera exposure_speed: {capture.exposure_speed}')
                            logging.info(f'camera awb_gains: {capture.awb_gains}')
                            logging.info(f'camera analog_gain: {float(capture.analog_gain)}')
                            logging.info(f'camera digital_gain: {float(capture.digital_gain)}')
                            logging.info(f'camera iso: {float(capture.iso)}')
 
                            # raw_capture.truncate()
                            # raw_capture.seek(0)
                            raw_capture.truncate(0)
                            logging.info('Success taking capture')
   
    
                            # out = np.copy(frame.array)
                            out = cv2.cvtColor(frame.array,cv2.COLOR_BGR2GRAY)
                            #fixme here we could actually pass a JPG compressed file object (http://docs.scipy.org/doc/scipy-0.16.0/reference/generated/scipy.misc.imsave.html)
                            # This way, we would manage to get faster FPS
                            self._queue.put(out)
                            trials = 0

                    except (PiCameraValueError, PiCameraRuntimeError) as error:
                        logging.warning(error)
                        logging.warning(traceback.print_exc())
                        trials += 1
                        recursion += 1
                        if trials == max_trials:
                            raise error

                        logging.warning('Failed %d times in a row. Trying again...', trials)
                        capture.close()
                        time.sleep(2)
                        capture_continuous(trials, recursion)
                        return

            capture_continuous(0, 0)
 
        except Exception as error:
            logging.warning(error)
            logging.warning(traceback.print_exc())

        finally:
            logging.warning(f"PID {os.getpid()}: Closing frame grabber process")
            self._stop_queue.close()
            self._queue.close()
            logging.warning(f"PID {os.getpid()}: Camera Frame grabber stopped acquisition cleanly")





class FSLPiCameraAsync(OurPiCameraAsync):
    _description = {"overview": "Default class to acquire frames from the raspberry pi camera asynchronously.",
                    "arguments": []}


    _frame_grabber_class = DualPiFrameGrabber
    def __init__(self, target_fps=2, target_resolution=(1280, 960), *args, **kwargs):
        """
        Class to acquire frames from the raspberry pi camera asynchronously.
        At the moment, frames are only greyscale images.

        :param target_fps: the desired number of frames par second (FPS)
        :type target_fps: int
        :param target_resolution: the desired resolution (W x H)
        :param target_resolution: (int,int)
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """
        logging.info(f"{os.getpid()} Initialising camera")
        self.canbepickled = True #cv2.videocapture object cannot be serialized, hence cannot be picked
        w,h = target_resolution
        if not isinstance(target_fps, int):
            raise EthoscopeException("FPS must be an integer number")
        self._args = args
        self._kwargs = kwargs
        self._queue = multiprocessing.Queue(maxsize=1)
        self._exposure_queue = multiprocessing.Queue(maxsize=2)

        self._stop_queue = multiprocessing.JoinableQueue(maxsize=1)
        self._p = self._frame_grabber_class(self._exposure_queue, target_fps, target_resolution, self._queue, self._stop_queue, *args, **kwargs)
        self._p.daemon = True
        self._p.start()

        try:
            try:
                im = self._queue.get(timeout=30)

            # to deal with broken camera thread. Just recreate it
            except (OSError, queue.Empty) as error:
                logging.warning("30 seconds timeout detected")
                logging.warning("Regenerating camera thread")
                self._queue = multiprocessing.Queue(maxsize=1)
                self._exposure_queue = multiprocessing.Queue(maxsize=2)
                self._stop_queue = multiprocessing.JoinableQueue(maxsize=1)
 
                self._p = self._frame_grabber_class(self._exposure_queue, target_fps, target_resolution, self._queue, self._stop_queue, *args, **kwargs)
                self._p.daemon = True
                self._p.start()
                im = self._queue.get(timeout=30)

               
        except Exception as error:
            logging.error("Could not get any frame from the camera")
            self._stop_queue.cancel_join_thread()
            self._queue.cancel_join_thread()
            logging.warning("Stopping stop queue")
            self._stop_queue.close()
            logging.warning("Stopping queue")
            self._queue.close()
            logging.warning("Joining process")
            # we kill the frame grabber if it does not reply within 10s
            self._p.join(10)
            logging.warning("Process joined")
            raise error

        self._frame = cv2.cvtColor(im,cv2.COLOR_GRAY2BGR)
        if len(im.shape) < 2:
            raise EthoscopeException("The camera image is corrupted (less that 2 dimensions)")
        self._resolution = (im.shape[1], im.shape[0])
        if self._resolution != target_resolution:
            if w > 0 and h > 0:
                logging.warning('Target resolution "%s" could NOT be achieved. Effective resolution is "%s"' % (target_resolution, self._resolution ))
            else:
                logging.info('Maximal effective resolution is "%s"' % str(self._resolution))
        super(OurPiCameraAsync, self).__init__(*args, **kwargs)
        self._start_time = time.time()
        logging.info("Camera initialised")


    def set_tracker(self):
        self._p._tracker_event.set()

    def change_gain(self, mean_intensity, means, mode, i=0):
        
        within = mean_intensity > means[mode][0] and mean_intensity < means[mode][1]
            
        if not within:
            gain = 'analog_gain' if mode == 'target_detection' else 'awb_gains'
            sign = 1 if mean_intensity < means[mode][0] else -1
            self._exposure_queue.put((gain, sign))
            time.sleep(1)
            return i
        else:
            return i + 1


    def set_roi_builder(self):
        self._p._roi_builder_event.set()
