#! /bin/bash

MACHINE_ID=$(cat /etc/machine-id)

curl --data "" -H "Content-Type:application/json" http://localhost:9000/controls/$MACHINE_ID/stop

