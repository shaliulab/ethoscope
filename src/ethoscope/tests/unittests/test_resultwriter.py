__author__ = "antonio"

import unittest
import pickle
import os.path
import multiprocessing
from ethoscope.utils.io import AsyncMySQLWriter, ResultWriter

db_credentials = {"name": "VIRTUAL_ETHOSCOPE_db", "user": "ethoscope", "password": "ethoscope"}
LOG_DIR = "./test_logs/"
def get_machine_name():
    return "VIRTUAL_ETHOSCOPE"

class TestResultWriter(unittest.TestCase):

    _async_writing_class = AsyncMySQLWriter
    _db_credentials = {
        "name": "%s_db" % get_machine_name(),
        "user": "ethoscope",
        "password": "ethoscope"
    }

    def setUp(self):

        with open(os.path.join(LOG_DIR, "TestFSLROIBuilder_rois.pickle"), "rb") as fh:
            rois = pickle.load(fh)

        self.rw = ResultWriter(self._db_credentials, rois)
        self.commands =  [
            "CREATE TABLE IF NOT EXISTS QC (t INT, mean_red FLOAT, mean_green FLOAT, mean_blue FLOAT,             min_red FLOAT, max_red FLOAT,             min_green FLOAT, max_green FLOAT,             min_blue FLOAT, max_blue FLOAT) ENGINE InnoDB KEY_BLOCK_SIZE=16;",
            "INSERT INTO QC (t, mean_red, mean_green, mean_blue, min_red, max_red, min_green, max_green, min_blue, max_blue)         VALUES (1587585129.2686825, 74.84170735677084, 74.84170735677084, 74.84170735677084,             0, 224, 0,             224, 0, 224)"
        ]



    def test_put(self, args=None):
        for command in self.commands:
            self.rw._queue.put((command, args))
            self.rw._queue.put("DONE")
            





