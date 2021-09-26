import logging


from ethoscope.roi_builders.automatic_roi_builder import AutomaticROIBuilder
from ethoscope.core.monitor import Monitor
from ethoscope.hardware.input.cameras import MovieVirtualCamera, ImgStoreCamera
from ethoscope.trackers.rich_adaptive_bg_tracker import RichAdaptiveBGModel
from ethoscope.utils.io import SQLiteResultWriter
from ethoscope.core.qc import QualityControl
from ethoscope.drawers.drawers import DefaultDrawer
# from ethoscope.stimulators.stimulators import DefaultStimulator
from ethoscope.web_utils.helpers import get_machine_id, get_machine_name

roi_builder = AutomaticROIBuilder(args=(), kwargs={"top_left": "(760, 180)", "roi_width": 3130, "roi_height": 231, "roi_offset": 340, "nrois": 9})
camera = ImgStoreCamera("./data/2021-09-26_15-07-37/")
rois = roi_builder.build(camera)

# just analyze the 4th fly
#rois = [rois[3]]

sensor = None
stimulators = None
drawer = DefaultDrawer(debug=True)
metadata = {
    "machine_id": get_machine_id(),
    "machine_name": get_machine_name(),
    "date_time": camera.start_time,  # the camera start time is the reference 0
    "frame_width": camera.width,
    "frame_height": camera.height,
    "version": "",
    "experimental_info": str({}),
    "selected_options": str({}),
}


output = "/ethoscope_data/results/5ce88718c3244cc88a1fa59d19099951/SUPERETHOSCOPE_001/2021-09-26_15-45-00/2021-09-26-15-45-00_5ce88718c3244cc88a1fa59d19099951.db"
db_credentials = {"name": output, "user": "ethoscope", "password": "ethoscope"}

logging.warning("Detected camera start time is %d", camera.start_time)
# hardware_interface is a running thread
result_writer = SQLiteResultWriter(db_credentials, rois, metadata=metadata, sensor=sensor, path=db_credentials["name"], make_dam_like_table=False)
quality_controller = QualityControl(result_writer)
monitor = Monitor(camera, RichAdaptiveBGModel, rois, stimulators=stimulators, debug=True, live_tracking=False)


monitor.run(result_writer, drawer, quality_controller)
