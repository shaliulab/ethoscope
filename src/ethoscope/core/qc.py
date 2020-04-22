from PIL import Image, ImageStat
import logging

class QualityControl:

    def __init__(self, result_writer):

        self.result_writer = result_writer

        result_writer._create_table(
            "QC", "t INT, mean FLOAT, min FLOAT, max FLOAT"
        )

        
    @staticmethod
    def image_stat(frame):
        current_image = Image.fromarray(frame)
        return ImageStat.Stat(current_image)

    def qc(self, frame):
        stat = self.image_stat(frame)
        return {"stat": stat}

    def write(self, t, qc):
        #(t, mean_red, mean_green, mean_blue, min_red, max_red, min_green, max_green, min_blue, max_blue) \
        tp = (t, qc['stat'].mean[0], qc['stat'].extrema[0][0], qc['stat'].extrema[0][1])

        command = f"INSERT INTO QC VALUES {str(tp)}"

        if "QC" not in self.result_writer._insert_dict or self.result_writer._insert_dict["QC"] == "":
        # if "QC" not in self.result_writer._insert_dict or self.result_writer._insert_dict == "":
            self.result_writer._insert_dict["QC"] = command
        else:
            self.result_writer._insert_dict["QC"] += ("," + str(tp))

    # only unit testing
    def flush(self, t, frame):
        self.result_writer.flush(t, frame)

