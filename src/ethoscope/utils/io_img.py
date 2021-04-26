import logging
logging.basicConfig(level=logging.DEBUG)
import tempfile
import os
import time, datetime
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

    def serialize_img(img, path):
        cv2.imwrite(self._tmp_file, img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])

        with open(self._tmp_file, "rb") as f:
            bstring = f.read()
        
        return bstring

class ImgToMySQLDebugHelper(ImgToMySQLHelper):
    _table_headers = {"id" : "INT NOT NULL AUTO_INCREMENT PRIMARY KEY",
                      "t"  : "INT",
                      "date": "date char(100)",
                      "time": "time char(100)",
                      "img" : "LONGBLOB",
                      "foreground": "LONGBLOB"
    }
                    

    _value_placeholders = {"MySQL": "(%s, %s, %s, %s, %s, %s)", "SQLite": "(?, ?, ?, ?, ?, ?)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tmp_file_fg = tempfile.mktemp(prefix="ethoscope_", suffix=".jpg")

    
    def stack_foreground(self, tracking_units, nrow=10, ncol=2):
        shape = np.vstack([t_u.tracker._foreground.shape for t_u in tracking_units])
        shape = shape.min(axis=0) # get smallest shape and use it for all
        # this means all foregrounds will have the smallest size that all can provide
        empty_foreground = np.zeros(shape, dtype=np.uint8)

        layout = [[None, ] * nrow, ] * ncol 
        
        for i, t_u in enumerate(tracking_units):
            col_idx = 0 if i < 10 else 1
            row_idx = i % 10
            try:
                foreground = t_u.tracker._foreground[:shape[0], :shape[1]]
            except Exception as error:
                logging.warning(error)
                foreground = empty_foreground
    
            layout[col_idx][row_idx] = foreground

        foreground = np.hstack([np.vstack(col) for col in layout])
        return foreground


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

        args = (identity, date_time_fields[0], date_time_fields[1], int(t), bstring, bstring_fg)

        self._last_tick = tick

        return cmd, args
