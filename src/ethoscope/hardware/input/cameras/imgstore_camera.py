import logging
import os.path
import tqdm
import cv2

from .cameras import MovieVirtualCamera
from imgstore import new_for_filename

class ImgStoreCamera(MovieVirtualCamera):
    """
    Class to acquire frames from an ImgStore using the ethoscope platform

    :param path: the path of the store
    :type path: str
    :param args: additional arguments.
    :param kwargs: additional keyword arguments.
    """

    def __init__(self, path, *args, drop_each=1, max_duration = None, **kwargs):

        #print "path", path
        logging.info(path)
        self._frame_idx = 0
        self._path = path
        self._use_wall_clock = False
        self._drop_each = drop_each
        self._max_duration = max_duration


        self._last_t = None
        self._last_count = None

        if not (isinstance(path, str) or isinstance(path, str)):
            raise EthoscopeException("path to video must be a string")
        if not os.path.exists(path):
            raise EthoscopeException("'%s' does not exist. No such file" % path)

        self.canbepickled = False #cv2.videocapture object cannot be serialized, hence cannot be picked

        store = new_for_filename(path)
        metadata = store.get_frame_metadata()
        self._store = store
        h, w = self._store._imgshape
        self._total_n_frames = len(metadata["frame_number"])

        self._tqdm = tqdm.tqdm(total=self._total_n_frames)

        if self._total_n_frames == 0.:
            self._has_end_of_file = False
        else:
            self._has_end_of_file = True


        self._start_time = metadata["frame_time"][0]
        self._resolution = (int(w),int(h))


    def _next_image(self):
        img, (frame_number, frame_timestamp) = self._store.get_next_image()
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        self._last_t = frame_timestamp
        self._last_count = frame_number
        self._frame_idx = frame_number
        return img

    def _time_stamp(self):
        return self._last_t


    def is_last_frame(self):
        return self._store.frame_max == self._last_count

    def _close(self):
        return self._store.close()


    def _next_time_image(self):
        img = self._next_image()
        return self._last_t, img

    

