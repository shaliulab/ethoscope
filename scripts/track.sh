#! /bin/bash

MACHINE_ID=$(cat /etc/machine-id)

DATA=$(echo "{'roi_builder': {'name': 'AutomaticROIBuilder', 'arguments': {'top_left': '(760, 180)', 'roi_width': 3130, 'roi_height': 231, 'roi_offset': 340, 'nrois': 9}}, 'tracker': {'name': 'RichAdaptiveBGModel', 'arguments': {'debug': 'False', 'scale_factor': 0.33}}, 'interactor': {'name': 'DefaultStimulator', 'arguments': {}}, 'camera': {'name': 'HRPiCameraAsync', 'arguments': {}}, 'result_writer': {'name': 'ResultWriter', 'arguments': {}}, 'experimental_info': {'name': 'ExperimentalInformation', 'arguments': {'name': '', 'location': '', 'code': ''}}}" | tr \' \")

curl --data "$DATA" -H "Content-Type:application/json" http://localhost:9000/controls/$MACHINE_ID/start

