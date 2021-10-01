#! /bin/bash

MACHINE_ID=$(cat /etc/machine-id)

DATA=$(echo "{'recorder': {'name': 'ImgStoreRecorder', 'arguments': {}}, 'experimental_info': {'name': 'ExperimentalInformation', 'arguments': {}}}" | tr \' \")
echo $DATA
curl --data "$DATA" -H "Content-Type:application/json" http://localhost:9000/controls/$MACHINE_ID/start_record

