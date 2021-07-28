import logging
logging.basicConfig(level=logging.DEBUG)
import tempfile
import os
import time, datetime

import numpy as np
import cv2

from ethoscope.utils.io_helpers import Null

class ImgToMySQLHelper(object):

    _table_name = "IMG_SNAPSHOTS"
    _table_headers = {"id" : "INT NOT NULL AUTO_INCREMENT PRIMARY KEY",
                      "t"  : "INT",
                      "img" : "LONGBLOB"}

    _value_placeholders = {"MySQL": "(%s, %s, %s)", "SQLite": "(?, ?, ?)"}
    _id_placeholders = {"MySQL": 0, "SQLite": Null()}

    @property
    def table_name (self):
        return self._table_name

    @property
    def create_command(self):
        return ",".join([ "%s %s" % (key, self._table_headers[key]) for key in self._table_headers])

    def placeholder(self, name="value"):
        if name == "value":
            return self._value_placeholders[self._sql_flavour]
        elif name == "id":
            return self._id_placeholders[self._sql_flavour]
        else:
            raise Exception("Invalid placeholder name. Please select value or id")

    def __init__(self, period=300.0, sql_flavour="MySQL"):
        """
        :param period: how often snapshots are saved, in seconds
        :return:
        """

        self._period = period
        self._last_tick = 0
        self._tmp_file = tempfile.mktemp(prefix="ethoscope_", suffix=".jpg")
        self._sql_flavour = sql_flavour

    def __del__(self):
        try:
            os.remove(self._tmp_file)
        except:
            logging.error("Could not remove temp file: %s", self._tmp_file)

    def flush(self, t, img, frame_idx=None):
        """
        :param t: the time since start of the experiment, in ms
        :param img: an array representing an image.
        :type img: np.ndarray
        :return:
        """

        tick = int(round((t/1000.0)/self._period))

        if tick == self._last_tick:
            return

        bstring = self._serialize_img(img, self._tmp_file)
        identity = self.placeholder("id")

        cmd = 'INSERT INTO ' + self._table_name + '(id,t,img) VALUES %s' % self.placeholder("value")

        args = (identity, int(t), bstring)

        self._last_tick = tick

        return cmd, args

    @staticmethod
    def _serialize_img(img, path):
        cv2.imwrite(path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])

        with open(path, "rb") as f:
            bstring = f.read()
        
        return bstring

class ImgToMySQLDebugHelper(ImgToMySQLHelper):
    _table_headers = {"id" : "INT NOT NULL AUTO_INCREMENT PRIMARY KEY",
                      "t"  : "INT",
                      "date": "char(100)",
                      "time": "char(100)",
                      "img" : "LONGBLOB",
                      "foreground": "LONGBLOB"
    }
                    

    _value_placeholders = {"MySQL": "(%s, %s, %s, %s, %s, %s)", "SQLite": "(?, ?, ?, ?, ?, ?)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tmp_file_fg = tempfile.mktemp(prefix="ethoscope_", suffix=".jpg")

    
    def stack_foreground(self, tracking_units, nrow=10, ncol=2):

        roi_to_col = {
                1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6:0, 7:0, 8:0, 9:0, 10:0,
                11: 1, 12: 1, 13: 1, 14: 1, 15: 1, 16:1, 17:1, 18:1, 19:1, 20:1
        }

        roi_to_row = {
                1: 0, 2: 1, 3: 2, 4:3, 5:4, 6:5, 7:6, 8:7, 9:8, 10:9,
                11: 0, 12: 1, 13: 2, 14:3, 15:4, 16:5, 17:6, 18:7, 19:8, 20:9,

        }
        # TODO Be smarter when _foreground is still None
        try:
            shape = np.vstack([t_u._tracker._foreground.shape for t_u in tracking_units])
            shape = shape.min(axis=0) # get smallest shape and use it for all
        except Exception as error:
            logging.warning(error)
            shape = np.array([40, 300])

        # this means all foregrounds will have the smallest size that all can provide
        empty_foreground = np.zeros(shape, dtype=np.uint8)

        columns = {"0": [None,]*nrow, "1": [None,]*nrow}
       
        for t_u in tracking_units[::-1]:
            i = t_u.roi._idx
            col_idx = roi_to_col[i]
            row_idx = roi_to_row[i]
            logging.warning("ROI: %d taking foreground", i)
            logging.warning("col: %d taking foreground", col_idx)
            logging.warning("row: %d taking foreground", row_idx)
            logging.warning("rectangle: %s", ",".join([str(e) for e in t_u.roi._rectangle]))
            try:
                foreground = t_u._tracker._foreground[:shape[0], :shape[1]]
            except Exception as error:
                logging.warning(error)
                foreground = empty_foreground
    
            columns[str(col_idx)][row_idx] = foreground.copy()

        layout_stack = np.hstack([
            np.vstack(columns["0"]),
            np.vstack(columns["1"])
        ])

        #layout_stack = None
        #for col in layout:
        #    if layout_stack is None:
        #        layout_stack = np.vstack(col)
        #    else:
        #        layout_stack = np.hstack([layout_stack, np.vstack(col)])
        #    break

        return layout_stack


    def flush(self, t, img, tracking_units=None, frame_idx=None):
        dt = datetime.datetime.fromtimestamp(int(time.time()))
        date_time_fields = dt.strftime("%d %b %Y,%H:%M:%S").split(",")

        tick = int(round((t/1000.0)/self._period))

        if tick == self._last_tick:
            return

        foreground = self.stack_foreground(tracking_units)

        bstring = self._serialize_img(img, self._tmp_file)
        bstring_fg = self._serialize_img(foreground, self._tmp_file_fg)
        
        identity = self.placeholder("id")

        cmd = 'INSERT INTO ' + self._table_name + '(id,t, date, time, img, foreground) VALUES %s' % self.placeholder("value")

        args = (identity, int(t), date_time_fields[0], date_time_fields[1], bstring, bstring_fg)

        self._last_tick = tick

        return cmd, args
