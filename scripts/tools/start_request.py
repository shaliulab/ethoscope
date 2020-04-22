from ethoscope_node.utils.device_scanner import EthoscopeScanner
from ethoscope_node.utils.backups_helpers import receive_devices
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
all_devices = receive_devices(server)
regexp = re.compile(f'{regex}')


data = {'roi_builder': {'name': 'DefaultROIBuilder', 'arguments': {}}, 'tracker': {'name': 'AdaptiveBGModel', 'arguments': {}}, 'interactor': {'name': 'DefaultStimulator', 'arguments': {}}, 'experimental_info': {'name': 'ExperimentalInformation', 'arguments': {'name': '', 'location': '', 'code': ''}}}

for id, d in all_devices.items():
    ethoscope_name = d['name']
    if regexp.search(ethoscope_name) and d['status'] in ['running', 'recording']:
        ip = d['ip']
        # defining the api-endpoint
        API_ENDPOINT = f'http://{ip}:9000/controls/{id}/start'
        # sending post request and saving response as response object
        logging.warning(f'Starting tracking on {ethoscope_name}')
        logging.warning(API_ENDPOINT)
        answer = input(f'Are you sure you want to stop {ethoscope_name}? Answer yes if you are:')
        if answer in ['y', 'yes']:
            r = requests.post(url = API_ENDPOINT, data = {})
        elif answer in ['q', 'quit']:
            raise Exception('Quitting')

