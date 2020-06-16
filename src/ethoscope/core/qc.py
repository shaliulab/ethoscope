import numpy as np
import logging
import time

class QualityControl:

    def __init__(self, result_writer):

        self.result_writer = result_writer

        result_writer._create_table(
            "QC", "t INT, mean FLOAT, min FLOAT, max FLOAT"
        )


    @staticmethod
    def image_stat(frame):

        logging.debug("----")
        logging.debug(time.time())
        mean = np.mean(frame)
        minimum = np.min(frame)
        maximum = np.max(frame)
        logging.debug(time.time())
        stats = {"mean": mean, "min": minimum, "max": maximum}
        logging.debug("----")
        return stats

    def qc(self, frame):
        stat = self.image_stat(frame)
        return {"stat": stat}

    def write(self, t, qc):
        #(t, mean_red, mean_green, mean_blue, min_red, max_red, min_green, max_green, min_blue, max_blue) \
        tp = (t, qc['stat']['mean'], qc['stat']['min'], qc['stat']['max'])

        command = f"INSERT INTO QC VALUES {str(tp)}"

        if "QC" not in self.result_writer._insert_dict or self.result_writer._insert_dict["QC"] == "":
        # if "QC" not in self.result_writer._insert_dict or self.result_writer._insert_dict == "":
            self.result_writer._insert_dict["QC"] = command
        else:
            self.result_writer._insert_dict["QC"] += ("," + str(tp))

    # only unit testing
    def flush(self, t, frame):
        self.result_writer.flush(t, frame)

