import logging


from ethoscope.roi_builders.automatic_roi_builder import AutomaticROIBuilder
from ethoscope.core.monitor import Monitor
from ethoscope.hardware.input.cameras import MovieVirtualCamera
from ethoscope.trackers.rich_adaptive_bg_tracker import RichAdaptiveBGModel
from ethoscope.utils.io import SQLiteResultWriter
from ethoscope.core.qc import QualityControl
from ethoscope.drawers.drawers import DefaultDrawer
# from ethoscope.stimulators.stimulators import DefaultStimulator
from ethoscope.web_utils.helpers import get_machine_id, get_machine_name

roi_builder = AutomaticROIBuilder()
camera = MovieVirtualCamera("./data/video.avi")
rois = roi_builder.build(camera)

# just analyze the 4th fly
rois = [rois[3]]

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

db_credentials = {"name": "result.db", "user": "ethoscope", "password": "ethoscope"}

logging.warning("Detected camera start time is %d", camera.start_time)
# hardware_interface is a running thread
result_writer = SQLiteResultWriter(db_credentials, rois, metadata=metadata, sensor=sensor, path=db_credentials["name"], make_dam_like_table=False)
quality_controller = QualityControl(result_writer)
monitor = Monitor(camera, RichAdaptiveBGModel, rois, stimulators=stimulators, debug=True, live_tracking=False)


monitor.run(result_writer, drawer, quality_controller)