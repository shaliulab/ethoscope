import requests
import argparse
import logging
import time
import re
import ipdb

ap = argparse.ArgumentParser()
ap.add_argument('-r', '--regex', type = str, required=False)
ap.add_argument("-i", "--server", dest="server", default="localhost", help="The server on which the node is running will be interrogated first for the device list")
args = vars(ap.parse_args())
server = args['server']
regex = args['regex']
regexp = re.compile(f'{regex}')

try:
    from ethoscope_node.utils.backups_helpers import receive_devices
    all_devices = receive_devices(server)
    running_local = False
except ModuleNotFoundError as e:
    from ethoscope.web_utils.helpers import get_machine_id, get_machine_name
    machine_id = get_machine_id()
    machine_name = get_machine_name()
    all_devices =  {machine_id: {"status": "stopped", "ip": "localhost", "name": machine_name}}
    running_local = True


data = {'roi_builder': {'name': 'DefaultROIBuilder', 'arguments': {}}, 'tracker': {'name': 'AdaptiveBGModel', 'arguments': {}}, 'interactor': {'name': 'DefaultStimulator', 'arguments': {}}, 'experimental_info': {'name': 'ExperimentalInformation', 'arguments': {'name': '', 'location': '', 'code': ''}}}

for id, d in all_devices.items():
    ethoscope_name = d['name']
    if (regexp.search(ethoscope_name) or running_local) and d['status'] in ['stopped']:
        ip = d['ip']
        # defining the api-endpoint
        API_ENDPOINT = f'http://{ip}:9000/controls/{id}/start'
        # sending post request and saving response as response object
        logging.warning(f'Starting tracking on {ethoscope_name}')
        logging.warning(API_ENDPOINT)
        r = requests.post(url = API_ENDPOINT, json = data)
        print(r)

