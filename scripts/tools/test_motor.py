import logging
import time
import serial
import os
import argparse
from serial.tools import list_ports

ap = argparse.ArgumentParser()

ap.add_argument('-m','--motors', nargs='+', help='<Required> Set flag', required=True)
ap.add_argument('-d', '--duration', type=int, default=1)
ap.add_argument('-w', '--wait', type=int, default=.5)
args = vars(ap.parse_args())

motor_map = {'1': 0, '2': 2, '3': 4, '4':6, '5':8, '6': 22, '7': 20, '8':18, '9': 16, '10': 14}

channels = []

for m in args['motors']:
    channels.append(motor_map[m])



baud = 115200

all_port_tuples = list_ports.comports()
logging.info("listing serial ports")
all_ports = set()

for ap, _, _ in all_port_tuples:
    p = os.path.basename(ap)
    print(p)
    if p.startswith("ttyUSB") or p.startswith("ttyACM"):
        all_ports |= {ap}
        print(len(all_ports))

port =  all_ports.pop()

handle = serial.Serial(port, baud, timeout =2)

intensity = 1000

duration = args['duration']*1000
wait = args['wait']

for c in channels:
    instruction = b"P %i %i %i\r" %(c, duration, intensity)
    handle.write(instruction)
    time.sleep(wait)

