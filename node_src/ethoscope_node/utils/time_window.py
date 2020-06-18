import logging
import os
import os.path
import re
import sqlite3
import traceback

import cv2
from ethoscope.core.roi import ROI
from ethoscope.core.variables import XPosVariable, YPosVariable, XYDistance, WidthVariable, HeightVariable, PhiVariable, BaseRelativeVariable
from ethoscope.core.tracking_unit import TrackingUnit
from ethoscope.core.data_point import DataPoint
from ethoscope.drawers.drawers import DefaultDrawer

logging.basicConfig(level=logging.INFO)

class TimeWindow(TrackingUnit):

    _CODEC = "XVID"
    _extension = "avi"

    def __init__(
            self, index, window_start, window_end, region_id, path,
            zt, max_velocity, activity,
            framerate=2, result_dir=".", input_video="video.mp4",
            all=True, annotate=False, informative=False
        ):

        self._index = index
        self._start = float(window_start) #s
        self._end = float(window_end) # s
        self._region_id = int(region_id)
        self._path = path
        self._result_dir = result_dir
        self._input_video = input_video
        self._all = all


        self.get_roi()
        self._framerate = framerate
        self._fourcc = cv2.VideoWriter_fourcc(*self._CODEC)
        self._cam = None
        self._frame_count = 0
        self.positions = []
        self._last_positions = {}
        self._xyshape_pad = (0, 0)
        self._video_writer = None
        self._max_velocity = max_velocity
        self._activity = activity
        self._annotate = annotate
        self._informative = informative
        self._zt = zt

        # TODO Use video generation functionality from the drawer classes!!!
        self.drawer = DefaultDrawer()


    @property
    def video_writer(self):
        return self._video_writer


    @property
    def _dbfile(self):

        dbfile = self._input_video.replace("videos", "results").replace("whole_", "").split("__")[0]
        prog = re.compile(r"(/ETHOSCOPE_([\d_PV])*/)")
        match = re.findall(prog, dbfile)
        match = match[0][0]
        dbfile = dbfile.replace(match, "/FLYSLEEPLAB_CV1/")
        dbfile += ".db"
        return dbfile


    @property
    def video_path(self):
        """
        Return a unique video name for each window
        given an input mp4 video and an iteration count
        """
        template = os.path.join(self._result_dir, "%s__ROI%s@t%s.%s")
        prog = re.compile(r"@(\d*_)")
        experiment_id = self._input_video.replace(re.findall(prog, self._input_video)[0], str(self._framerate).zfill(2) + "_")
        experiment_id = os.path.basename(experiment_id.replace(".mp4", ""))

        if self._informative:
            prefix = str(self._max_velocity).zfill(10)[:10] + "_" + experiment_id
        else:
            prefix = experiment_id

        filename = template % (
            prefix,
            str(self._region_id).zfill(2),
            str(int(self.start*1000)).zfill(9),
            self._extension

        )

        return filename

    @property
    def resolution(self):
        return (self.width, self.height)

    @property
    def width(self):
        if self.roi is None:
            return 1280
        else:
            return self.roi.rectangle[2]

    @property
    def height(self):
        if self.roi is None:
            return 960
        else:
            return self.roi.rectangle[3]


    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    @property
    def start_fragment(self):
        return self._start * 1000

    @property
    def end_fragment(self):
        return self._end * 1000


    def open(self, cam):
        logging.info("Moving video to %d ms", self.start_fragment)
        cam.capture.set(cv2.CAP_PROP_POS_MSEC, self.start_fragment)
        frame_index = cam.capture.get(cv2.CAP_PROP_POS_FRAMES)
        pos_msec = cam.capture.get(cv2.CAP_PROP_POS_MSEC)
        logging.info("Opening window starting in frame %d at %d ms", frame_index, pos_msec)
        self._cam = cam

    def get_roi(self):

        if self._region_id == 0:
            self._roi = None
            return

        with sqlite3.connect(self._dbfile, check_same_thread=False) as src:
            src_cur = src.cursor()
            command = "SELECT x, y, w, h from ROI_MAP WHERE roi_idx = %d" % self._region_id
            src_cur.execute(command)
            xpos, ypos, width, height = next(iter(src_cur))
            polygon = [
                [xpos, ypos],               # tl
                [xpos+width, ypos],         # tr
                [xpos+width, ypos+height],  # br
                [xpos, ypos+height]         # bl
            ]
            roi = ROI(polygon, self._region_id)
            self._roi = roi
            # self._resolution_pad = (self._roi._rectangle[2], self._roi._rectangle[3])

    @property
    def _tracker(self):
        return self


    def apply(self, img):

        if self.roi is None:
            return img, None

        out, mask = self.roi.apply(img)
        return out, mask

    @property
    def camera_iterator(self):
        if self._cam.__class__.__name__ == "FSLVirtualCamera":
            cam_iterator = self._cam

        else:
            cam_iterator = enumerate(self._cam)

        return cam_iterator

    def run(self):

        if not self._annotate or self._region_id == 0:
            self._run(cursor=None)

        else:

            with sqlite3.connect(self._dbfile, check_same_thread=False) as con:
                cursor = con.cursor()
                self._run(cursor=cursor)


    def get_last_positions(self, absolute=False):
        """
        The last position of the animal monitored by this `TrackingUnit`

        :param absolute: Whether the position should be relative to the top left corner of the raw frame (`true`),
        or to the top left of the used ROI (`false`).
        :return: A container with the last variable recorded for this roi.
        :rtype:  :class:`~ethoscope.core.data_point.DataPoint`
        """

        if len(self.positions) < 1:
            return []

        last_positions = self.positions[-1]
        if not absolute:
            return last_positions
        out = []
        last_pos = last_positions
        #for last_pos in last_positions:
        tmp_out = []
        for i in list(last_pos.values()):
            if isinstance(i, BaseRelativeVariable):
                tmp_out.append(i.to_absolute(self.roi))
            else:
                tmp_out.append(i)
        tmp_out = DataPoint(tmp_out)
        out.append(tmp_out)

        return out

    @property
    def xyshape(self):
        r"""
        Emulate numpy shape without the channels
        i.e. without the third dimension,
        just return number of rowsxnumber of columns.
        """

        _, _, width, height = self._roi._rectangle
        return (height, width)


    @property
    def xyshape_pad(self):
        return self._xyshape_pad

    @xyshape_pad.setter
    def xyshape_pad(self, value):
        self._xyshape_pad = value

        self._video_writer = cv2.VideoWriter(
            # input .mp4
            self.video_path,
            # codec configuration
            self._fourcc,
            # framerate of the output, given by user input
            self._framerate,
            # resolution of the output video,
            # should be the reverse of the padded shape
            # i.e. the shape is #rowsx#columns
            # and we need here #columnsx#rows
            self.xyshape_pad[::-1]
        )


    def adjust(self, image):
        r"""
        Fill the window with black pixels so all windows
        have xyshape_pad.
        xyshape_pad should be set after initialising all windows
        and screening their rois.
        """
        bottom = max(self.xyshape_pad[0] - image.shape[0], 0)
        right = max(self.xyshape_pad[1] - image.shape[1], 0)
        border_type = cv2.BORDER_CONSTANT
        value = 0
        dst = cv2.copyMakeBorder(image, 0, bottom, 0, right, border_type, None, value)
        try:
            assert dst.shape[:2] == self.xyshape_pad
        except AssertionError as error:
            logging.warning(dst.shape)
            logging.warning(self.xyshape_pad)
            logging.warning(bottom)
            logging.warning(right)
            raise error

        return dst

    def _run(self, cursor=None):

        try:
            for index, (t_ms, img) in self.camera_iterator:
                if t_ms > self.end_fragment:
                    break

                if cursor:
                    template = "SELECT x, y, w, h, phi, xy_dist_log10x1000 FROM ROI_%d WHERE t = %d"
                    command = template % (self._region_id, t_ms)
                    cursor.execute(command)
                    try:
                        X = next(iter(cursor))
                    except Exception:
                        # an exception will happen when the t queried
                        # is not available in the dbfile
                        # even though it is in the video
                        # this happens if the dbfile is generated
                        # passing a drop-each argument != 1
                        # i.e. the dbfile is subsampled
                        if self._all:
                            self.add(img)
                        continue

                    xpos, ypos, width, height, phi, xy_dist = X
                    x_var = XPosVariable(xpos)
                    y_var = YPosVariable(ypos)
                    h_var = HeightVariable(height)
                    w_var = WidthVariable(width)
                    phi_var = PhiVariable(phi)
                    distance = XYDistance(xy_dist)
                    point = DataPoint([
                        x_var, y_var, w_var, h_var,
                        phi_var, distance
                    ])
                    self.positions.append(point)
                    abs_pos = self.get_last_positions(absolute=True)
                    self._last_positions[self.roi.idx] = abs_pos
                    out = self.drawer.draw(
                        img,
                        tracking_units=[self],
                        positions=self._last_positions,
                        roi=True
                    )

                else:
                    out = img

                self.add(out)

        except Exception as error:
            logging.error(traceback.print_exc())
            raise error

    def add(self, img):
        self._frame_count += 1
        logging.debug("Adding frame %d", self._frame_count)
        applied_img = self.apply(img)[0]
        adj_img = self.adjust(applied_img)
        self.video_writer.write(adj_img)

    def close(self):
        self.video_writer.release()
        logging.info("%d frames saved", self._frame_count)
        logging.info("Saving video to %s", self.video_path)

    def __repr__(self):
        template = "TimeWindow instance running %3.f-%3.f@region_id %d"
        return template % (self.start, self.end, self._region_id)
