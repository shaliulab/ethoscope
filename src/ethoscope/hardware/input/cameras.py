__author__ = 'quentin'

import time
import logging
logging.basicConfig(level=logging.INFO)
import os
import re
import datetime
import threading

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

from ethoscope.utils.claim_camera import claim_camera, remove_pidfile
from ethoscope.hardware.input.camera_settings import configure_camera

class BaseCamera(object):
    capture = None
    _resolution = None
    _frame_idx = 0

    def __init__(self, drop_each=1, max_duration=None, *args, **kwargs):
        """
        The template class to generate and use video streams.

        :param drop_each: keep only ``1/drop_each``'th frame
        :param max_duration: stop the video stream if ``t > max_duration`` (in seconds).
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """

        self._drop_each = drop_each
        self._max_duration = max_duration

    def __exit__(self):
        logging.info("Closing camera")
        self._close()

    def _close(self):
        pass

    def __iter__(self):
        """
        Iterate thought consecutive frames of this camera.

        :return: the time (in ms) and a frame (numpy array).
        :rtype: (int, :class:`~numpy.ndarray`)
        """
        at_least_one_frame = False
        while True:
            if self.is_last_frame() or not self.is_opened():
                if not at_least_one_frame:
                    raise EthoscopeException("Camera could not read the first frame")
                break
            t,out = self._next_time_image()
            if out is None:
                break
            t_ms = int(1000*t)
            at_least_one_frame = True

            if (self._frame_idx % self._drop_each) == 0:
                yield t_ms,out

            if self._max_duration is not None and t > self._max_duration:
                break


    def set_tracker(self):
        pass

    def set_roi_builder(self):
        pass

    @property
    def resolution(self):
        """

        :return: The resolution of the camera W x H.
        :rtype: (int, int)
        """
        return self._resolution

    @property
    def width(self):
        """
        :return: the width of the returned frames
        :rtype: int
        """
        return self._resolution[0]

    @property
    def height(self):
        """
        :return: the height of the returned frames
        :rtype: int
        """
        return self._resolution[1]

    def _next_time_image(self):
        time = self._time_stamp()
        im = self._next_image()
        self._frame_idx += 1
        return time, im

    def is_last_frame(self):
        raise NotImplementedError

    def _next_image(self):
        raise NotImplementedError

    def _time_stamp(self):
        raise NotImplementedError

    def is_opened(self):
        raise NotImplementedError

    def restart(self):
        """
        Restarts a camera (also resets time).
        :return:
        """
        raise NotImplementedError


class MovieVirtualCamera(BaseCamera):
    _description = {"overview":  "Class to acquire frames from a video file.",
                    "arguments": [
                                    {"type": "filepath", "name": "path", "description": "The *LOCAL* path to the video file to use as virtual camera","default":""},
                                   ]}


    def __init__(self, path, use_wall_clock=False, *args, **kwargs ):
        """
        Class to acquire frames from a video file.

        :param path: the path of the video file
        :type path: str
        :param use_wall_clock: whether to use the real time from the machine (True) or from the video file (False).\
            The former can be useful for prototyping.
        :type use_wall_clock: bool
        :param args: additional arguments.
        :param kwargs: additional keyword arguments.
        """

        #print "path", path
        logging.warning(path)
        self._frame_idx = 0
        self._path = path
        self._use_wall_clock = use_wall_clock


        if not (isinstance(path, str) or isinstance(path, str)):
            raise EthoscopeException("path to video must be a string")
        if not os.path.exists(path):
            raise EthoscopeException("'%s' does not exist. No such file" % path)

        self.canbepickled = False #cv2.videocapture object cannot be serialized, hence cannot be picked
        self.capture = cv2.VideoCapture(path)
        w = self.capture.get(CAP_PROP_FRAME_WIDTH)
        h = self.capture.get(CAP_PROP_FRAME_HEIGHT)
        self._total_n_frames =self.capture.get(CAP_PROP_FRAME_COUNT)
        if self._total_n_frames == 0.:
            self._has_end_of_file = False
        else:
            self._has_end_of_file = True

        self._resolution = (int(w),int(h))

        super(MovieVirtualCamera, self).__init__(*args, **kwargs)

        # emulates v4l2 (real time camera) from video file
        if self._use_wall_clock:
            self._start_time = time.time()
        else:
            self._start_time = 0

    @property
    def start_time(self):
        return self._start_time

    @property
    def path(self):
        return self._path

    def is_opened(self):
        return True

    def restart(self):
        self.__init__(self._path, use_wall_clock=self._use_wall_clock, drop_each=self._drop_each, max_duration = self._max_duration)


    def _next_image(self):
        _, frame = self.capture.read()
        return frame

    def _time_stamp(self):
        if self._use_wall_clock:
            now = time.time()
            return now - self._start_time
        time_s = self.capture.get(CAP_PROP_POS_MSEC) / 1e3
        return time_s

    def is_last_frame(self):
        if self._has_end_of_file and self._frame_idx >= self._total_n_frames:
            return True
        return False

    def _close(self):
        self.capture.release()


class FSLVirtualCamera(MovieVirtualCamera):
    """
    A MovieVirtualCamera with two features:
    * the _start_time is not 0 when using the wall_clock,
    instead it is the start of the video. This way the date_time
    field in the METADATA SQL table is not 0

    * its __iter__ method returns the frame count as stored in the
    _frame_idx attribute (without the need to call enumerate)
    """

    _ref_time = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

    def __init__(self, *args, **kwargs):

        super(FSLVirtualCamera, self).__init__(*args, **kwargs)
        # dont set _start_time to 0
        # instead use the same start_time as the video
        # this does not break the internal time counting system
        # when use_wall_clock false because the time is extracted with
        # cv2.cv.CAP_PROP_POS_MSEC without the need to substract the start
        self._start_time = self._parse_start_time()

    def _next_time_image(self):
        time, im = super()._next_time_image()
        frame_idx = self._frame_idx
        return frame_idx, (time, im)

    def _parse_start_time(self):
        logging.warning(self._path)

        res = re.findall(r"(\d{4}((-\d\d){2})_((\d\d-){2})\d{2})", self._path)
        logging.warning(res)
        assert res[0][0] == res[1][0]
        date_time_str = res[0][0]

        logging.warning("DATE_TIME_STR")
        logging.warning(date_time_str)
        date_time_naive = datetime.datetime.strptime(date_time_str, '%Y-%m-%d_%H-%M-%S')
        date_time_aware = date_time_naive.astimezone(datetime.timezone.utc)

        logging.warning("DATE_TIME")
        logging.warning(date_time_aware)
        # return the difference between the start of the video
        # and the reference time, set to 1970-01-01 00:00:00
        # in seconds
        # this emulates what we would get if we were producing the dbfile
        # via live and not offline tracking
        return (date_time_aware - self._ref_time).total_seconds()

    def __iter__(self):
        """
        Iterate thought consecutive frames of this camera.

        :return: the time (in ms) and a frame (numpy array).
        :rtype: (int, :class:`~numpy.ndarray`)
        """
        at_least_one_frame = False
        while True:
            if self.is_last_frame() or not self.is_opened():
                if not at_least_one_frame:
                    raise EthoscopeException("Camera could not read the first frame")
                break
            frame_idx, (t,out) = self._next_time_image()

            if out is None:
                break
            t_ms = int(1000*t)
            at_least_one_frame = True

            if (self._frame_idx % self._drop_each) == 0:
                yield frame_idx, (t_ms,out)

            if self._max_duration is not None and t > self._max_duration:
                break



class V4L2Camera(BaseCamera):
    _description = {"overview": "Class to acquire frames from the V4L2 default interface (e.g. a webcam).",
                    "arguments": [
                    {"type": "number", "min": 0, "max": 4, "step": 1, "name": "device", "description": "The device to be open", "default":0},
                    ]}

    def __init__(self, device=0, target_fps=5, target_resolution=(960,720), *args, **kwargs):
        """
        class to acquire stream from a video for linux compatible device (v4l2).

        :param device: The index of the device, or its path.
        :type device: int or str
        :param target_fps: the desired number of frames par second (FPS)
        :type target_fps: int
        :param target_fps: the desired resolution (W x H)
        :param target_resolution: (int,int)
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """

        self.canbepickled = False
        self.capture = cv2.VideoCapture(device)
        self._warm_up()

        w, h = target_resolution
        if w <0 or h <0:
            self.capture.set(CAP_PROP_FRAME_WIDTH, 99999)
            self.capture.set(CAP_PROP_FRAME_HEIGHT, 99999)
        else:
            self.capture.set(CAP_PROP_FRAME_WIDTH, w)
            self.capture.set(CAP_PROP_FRAME_HEIGHT, h)

        if not isinstance(target_fps, int):
            raise EthoscopeException("FPS must be an integer number")

        if target_fps < 2:
            raise EthoscopeException("FPS must be at least 2")
        self.capture.set(CAP_PROP_FPS, target_fps)

        self._target_fps = float(target_fps)
        _, im = self.capture.read()

        # preallocate image buffer => faster
        if im is None:
            raise EthoscopeException("Error whist retrieving video frame. Got None instead. Camera not plugged?")

        self._frame = im

        assert(len(im.shape) >1)

        self._resolution = (im.shape[1], im.shape[0])
        if self._resolution != target_resolution:
            if w > 0 and h > 0:
                logging.warning('Target resolution "%s" could NOT be achieved. Effective resolution is "%s"' % (target_resolution, self._resolution ))
            else:
                logging.info('Maximal effective resolution is "%s"' % str(self._resolution))


        super(V4L2Camera, self).__init__(*args, **kwargs)
        self._start_time = time.time()

    def _warm_up(self):
        logging.info("%s is warming up" % (str(self)))
        time.sleep(2)

    def restart(self):
        self._frame_idx = 0
        self._start_time = time.time()

    def is_opened(self):
        return self.capture.isOpened()

    def is_last_frame(self):
        return False

    def _time_stamp(self):
        now = time.time()
        # relative time stamp
        return now - self._start_time
    @property
    def start_time(self):
        return self._start_time

    def _close(self):
        self.capture.release()
    def _next_image(self):
        if self._frame_idx >0 :
            expected_time =  self._start_time + self._frame_idx / self._target_fps
            now = time.time()
            to_sleep = expected_time - now
            # Warnings if the fps is so high that we cannot grab fast enough
            if to_sleep < 0:
                if self._frame_idx % 5000 == 0:
                    logging.warning("The target FPS (%f) could not be reached. Effective FPS is about %f" % (self._target_fps, self._frame_idx/(now - self._start_time)))
                self.capture.grab()

            # we simply drop frames until we go above expected time
            while now < expected_time:
                self.capture.grab()
                now = time.time()
        else:
            self.capture.grab()
        self.capture.retrieve(self._frame)
        return self._frame


class PiFrameGrabber(threading.Thread):

    def __init__(self, target_fps, target_resolution, queue, stop_queue, *args, **kwargs):
        """
        Class to grab frames from pi camera. Designed to be used within :class:`~ethoscope.hardware.camreras.camreras.OurPiCameraAsync`
        This allows to get frames asynchronously as acquisition is a bottleneck.
        :param target_fps: desired fps
        :type target_fps: int
        :param target_resolution: the desired resolution (w, h)
        :type target_resolution: (int, int)
        :param queue: a queue that stores frame and makes them available to the parent process
        :type queue: :class:`~threading.JoinableQueue`
        :param stop_queue: a queue that can stop the async acquisition
        :type stop_queue: :class:`~threading.JoinableQueue`
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """

        self._queue = queue
        self._stop_queue = stop_queue
        self._target_fps = target_fps
        self._target_resolution = target_resolution
        logging.warning('PiFrameGrabber queue %s', queue)
        logging.warning('PiFrameGrabber stop_queue %s', stop_queue)
        logging.warning('PiFrameGrabber target_fps %s', target_fps)
        logging.warning('PiFrameGrabber target_resolution %s', target_resolution)
        
        super(PiFrameGrabber, self).__init__()


    def run (self):
        """
        Initialise pi camera, get frames, convert them fo greyscale, and make them available in a queue.
        Run stops if the _stop_queue is not empty.
        """

        try:
            # lazy import should only use those on devices
            
            # Warning: the following causes a major issue with Python 3.8.1
            # https://www.bountysource.com/issues/86094172-python-3-8-1-typeerror-vc_dispmanx_element_add-argtypes-item-9-in-_argtypes_-passes-a-union-by-value-which-is-unsupported
            # this should now be fixed in Python 3.8.2 (6/5/2020)
            
            import picamera
            import picamera.array

            with picamera.PiCamera() as capture:

                capture.resolution = self._target_resolution
                camera_info = capture.exif_tags
                logging.info("Detected camera %s: " % camera_info)
                
                #PINoIR v1
                #{'IFD0.Model': 'RP_ov5647', 'IFD0.Make': 'RaspberryPi'}
                #PINoIR v2
                #{'IFD0.Model': 'RP_imx219', 'IFD0.Make': 'RaspberryPi'}
                
                #disable auto white balance to address the following issue: https://github.com/raspberrypi/firmware/issues/1167
                #however setting this to off would have to be coupled with custom gains
                #some suggestion on how to set the gains can be found here: https://picamera.readthedocs.io/en/release-1.12/recipes1.html
                #and here: https://github.com/waveform80/picamera/issues/182
                
                if camera_info['IFD0.Model'] == 'RP_imx219':
                    capture.awb_mode = 'off'
                    capture.awb_gains = (1.8, 1.5) #TODO: allow user-specified gains
                    logging.info("piNoIR v2 detected - using custom awb parameters")
                else:
                    # we are disabling auto white balance for IMX219
                    capture.awb_mode = 'auto'
                    logging.info("piNoIR v1 detected - using automatic white balance")
                    
                #we save this information on the filesystem so that it can be retrieved by the system - this is not ideal but accessing IFD0 from another instance creates weird issues
                with open('/etc/picamera-version', 'w') as outfile:
                    print(camera_info, file=outfile)
                
                capture.framerate = self._target_fps
                stream = picamera.array.PiRGBArray(capture, size=self._target_resolution)
                time.sleep(0.2) # sleep 200ms to allow the camera to warm up

                for frame in capture.capture_continuous(stream, format="bgr", use_video_port=True):
                    
                    #This syntax changed from picamera > 1.7    - see https://picamera.readthedocs.io/en/release-1.10/deprecated.html
                    stream.seek(0)
                    stream.truncate()
                    # out = np.copy(frame.array)
                    out = cv2.cvtColor(frame.array,cv2.COLOR_BGR2GRAY)
                    #fixme here we could actually pass a JPG compressed file object (http://docs.scipy.org/doc/scipy-0.16.0/reference/generated/scipy.misc.imsave.html)
                    # This way, we would manage to get faster FPS
                    self._queue.put(out)

                    if not self._stop_queue.empty():
                        logging.info("The stop queue is not empty. This signals it is time to stop acquiring frames")
                        self._stop_queue.get()
                        self._stop_queue.task_done()
                        break

        except:
            logging.warning("Some problem acquiring frames from the camera")
                    
        finally:
            self._queue.task_done() # this tell the parent the thread can be closed
            logging.warning("Camera Frame grabber stopped acquisition cleanly")

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
            # lazy import should only use those on devices

            # Warning: the following causes a major issue with Python 3.8.1
            # https://www.bountysource.com/issues/86094172-python-3-8-1-typeerror-vc_dispmanx_element_add-argtypes-item-9-in-_argtypes_-passes-a-union-by-value-which-is-unsupported
            from picamera.array import PiRGBArray
            from picamera import PiCamera

            with claim_camera(framerate=self._target_fps, resolution=self._target_resolution) as capture:
            # wrap the call to picamera.PiCamera around a handler that
            # 1. creates a pidfile so the PID of the thread can be easily tracked
            # 2. removes a potential existing pidfile and kills the corresponding process
            # This is intended to avoid the Out of resources error caused by the camera thread not stopping upon monitor stop
                logging.warning(capture)
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
                i = 0

                for frame in capture.capture_continuous(raw_capture, format="bgr", use_video_port=True):

                    try:
                        gain, sign = self._exposure_queue.get(block=False)
                        capture = self.adjust_camera(capture, gain, sign)

                    except queue.Empty:
                        pass

                    if self._tracker_event.is_set() and not tracker_event:
                        capture = configure_camera(capture, mode="tracker")
                        tracker_event = True

                    if self._roi_builder_event.is_set() and not roi_builder_event:
                        capture = configure_camera(capture, mode="roi_builder")
                        roi_builder_event = True

                    if not self._stop_queue.empty():
                        logging.warning(f"PID {os.getpid()}: The stop queue is not empty. Stop acquiring frames")

                        self._stop_queue.get()
                        self._stop_queue.task_done()
                        logging.warning("Stop Task Done")
                        break

                    logging.warning(f'camera framerate: {capture.framerate}')
                    logging.warning(f'camera resolution: {capture.resolution}')
                    logging.warning(f'camera exposure_mode: {capture.exposure_mode}')
                    logging.warning(f'camera shutter_speed: {capture.shutter_speed}')
                    logging.warning(f'camera exposure_speed: {capture.exposure_speed}')
                    logging.warning(f'camera awb_gains: {capture.awb_gains}')
                    logging.warning(f'camera analog_gain: {float(capture.analog_gain)}')
                    logging.warning(f'camera digital_gain: {float(capture.digital_gain)}')
                    logging.warning(f'camera iso: {float(capture.iso)}')

                    raw_capture.truncate(0)
                    # out = np.copy(frame.array)
                    out = cv2.cvtColor(frame.array,cv2.COLOR_BGR2GRAY)
                    #fixme here we could actually pass a JPG compressed file object (http://docs.scipy.org/doc/scipy-0.16.0/reference/generated/scipy.misc.imsave.html)
                    # This way, we would manage to get faster FPS
                    #cv2.imwrite(f"/root/frame_{str(i).zfill(2)}.png", out)
                    self._queue.put(out)
                    i+= 1
        finally:
            # remove the pidfile created in claim_camera()
            remove_pidfile()
            logging.warning(f"PID {os.getpid()}: Closing frame grabber process")
            self._stop_queue.close()
            self._queue.close()
            logging.warning(f"PID {os.getpid()}: Camera Frame grabber stopped acquisition cleanly")


class OurPiCameraAsync(BaseCamera):
    _description = {"overview": "Default class to acquire frames from the raspberry pi camera asynchronously.",
                    "arguments": []}
                                   

    _frame_grabber_class = PiFrameGrabber
    def __init__(self, target_fps=20, target_resolution=(1280, 960), *args, **kwargs):
        """
        Class to acquire frames from the raspberry pi camera asynchronously.
        At the moment, frames are only greyscale images.
        :param target_fps: the desired number of frames par second (FPS)
        :type target_fps: int
        :param target_fps: the desired resolution (W x H)
        :param target_resolution: (int,int)
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """
        self.canbepickled = True #cv2.videocapture object cannot be serialized, hence cannot be picked

        w,h = target_resolution
        if not isinstance(target_fps, int):
            raise EthoscopeException("FPS must be an integer number")

        self._args = args
        self._kwargs = kwargs

        self._queue = queue.Queue(maxsize=1)
        self._stop_queue = queue.Queue(maxsize=1)

        self._p = self._frame_grabber_class(target_fps, target_resolution, self._queue, self._stop_queue, *args, **kwargs)

        self._p.daemon = True
        self._p.start()
        
        try:
            im = self._queue.get(timeout=10)
            
        except Exception as e:
            logging.error("Could not get any frame from the camera after the initialisation!")
            # we force kill the frame grabber if it does not reply within 5s
            self._p.join(5)
            logging.warning("Framegrabber thread joined")

            raise e
            
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

    def restart(self):
        self._frame_idx = 0
        self._start_time = time.time()

    def __getstate__(self):
        return {"args": self._args,
                "kwargs": self._kwargs,
                "frame_idx": self._frame_idx,
                "start_time": self._start_time}

    def __setstate__(self, state):
        self.__init__(*state["args"], **state["kwargs"])
        self._frame_idx = int(state["frame_idx"])
        self._start_time = int(state["start_time"])

    def is_opened(self):
        return True
        # return self.capture.isOpened()

    def is_last_frame(self):
        return False

    def _time_stamp(self):
        now = time.time()
        # relative time stamp
        return now - self._start_time

    @property
    def start_time(self):
        return self._start_time

    def _close(self):

        logging.info("Requesting grabbing process to stop!")
        
        #Insert a stop signal in the stopping queue
        self._stop_queue.put(None)
        
        #empty the frames' queue
        while not self._queue.empty():
             self._queue.get()

        self._p.join()
        logging.info("Frame grabbing thread is joined")

    def _next_image(self):
        try:
            g = self._queue.get(timeout=30)
            cv2.cvtColor(g,cv2.COLOR_GRAY2BGR,self._frame)
            return self._frame
        except Exception as e:
            raise EthoscopeException("Could not get frame from camera\n%s", traceback.format_exc())


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
            im = self._queue.get(timeout=30)
        except Exception as e:
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
            raise e
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

    def change_gain(self, gain, sign):
        self._exposure_queue.put((gain, sign))

    def set_roi_builder(self):
        self._p._roi_builder_event.set()


class DummyFrameGrabber(multiprocessing.Process):
    def __init__(self, target_fps, target_resolution, queue, stop_queue, path, *args, **kwargs):
        """
        Class to mimic the behaviour of :class:`~ethoscope.hardware.input.cameras.PiFrameGrabber`.
        This is intended for testing purposes.
        This way, we can emulate the async functionality of the hardware camera by a video file.

        :param target_fps: the desired number of frames par second (FPS)
        :type target_fps: int
        :param target_fps: the desired resolution (W x H)
        :param target_resolution: (int,int)
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """
        self._queue = queue
        self._stop_queue = stop_queue
        self._target_fps = target_fps
        self._target_resolution = target_resolution
        self._video_file = path
        super(DummyFrameGrabber, self).__init__()
    def run(self):
        try:

            cap = cv2.VideoCapture(self._video_file)
            while True:
                if not self._stop_queue.empty():

                    logging.warning("The stop queue is not empty. Stop acquiring frames")
                    self._stop_queue.get()
                    self._stop_queue.task_done()
                    logging.warning("Stop Task Done")
                    break
                _, out = cap.read()
                #todo sleep here
                out = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
                self._queue.put(out)

        finally:
            logging.warning("Closing frame grabber process")
            self._stop_queue.close()
            self._queue.close()
            logging.warning("Camera Frame grabber stopped acquisition cleanly")

class DummyPiCameraAsync(OurPiCameraAsync):
    """
    Class to mimic the behaviour of :class:`~ethoscope.hardware.input.cameras.OurPiCameraAsync`.
    This is intended for testing purposes. This way, we can emulate the async functionality of the hardware camera by a video file.
    """
    _frame_grabber_class = DummyFrameGrabber
