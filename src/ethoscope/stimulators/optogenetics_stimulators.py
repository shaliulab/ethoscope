'''
any new class added here need to be added to web_utils/control_thread.py too
'''

__author__ = 'quentin'


from ethoscope.stimulators.sleep_depriver_stimulators import RobustSleepDepriver, RobustOptomotorSleepDepriverSystematic
from ethoscope.hardware.interfaces.optogenetics import OptogeneticHardware
from ethoscope.stimulators.stimulators import HasInteractedVariable

import random
import time
import logging

class OptogeneticStimulator(RobustSleepDepriver):
    """
    Optogenetics stimulator using new PCB from Giorgio Gilestro.
    """
    _description = {"overview": "A stimulator to sleep deprive an animal using optogenetics",
                "arguments": [
                    {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
                    {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken(s)","default":10},
                    {"type": "number", "min": 10, "max": 10000 , "step": 10, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
                    {"type": "str", "name": "date_range",
                        "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                        "default": ""},
                    {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_on", "description": "duration of pulse in ms", "default": 50},
                    {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_off", "description": "resting time between pulses in ms", "default": 50},
                ]}

    _duration = 100
    _HardwareInterfaceClass = OptogeneticHardware
    def __init__(self,
                 *args,
                 pulse_on=50,
                 pulse_off=50,
                 **kwargs
                 ):
      
        self._pulse_on = pulse_on
        self._pulse_off = pulse_off
        super().__init__(*args, **kwargs)


    def _decide(self):
        out, dic = super(OptogeneticStimulator, self)._decide()
        dic["pulse_on"] = self._pulse_on
        dic["pulse_off"] = self._pulse_off
        return out, dic

class OptogeneticStimulatorSystematic(RobustOptomotorSleepDepriverSystematic):
    _description = {
        "overview": "A stimulator to sleep deprive an animal using optogenetics at a constant interval",
        "arguments": [
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "interval", "description": "The recurrence of the stimulus","default":1},
            {"type": "number", "min": 10, "max": 10000 , "step": 10, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms). Please pass 3000 if you want a permanent (constant) stimulus (still oscillating and only within the date range). If you pass less, there will be brief periods without light. Check beforehand in that case.", "default": 3000},
            {"type": "str", "name": "date_range",
                "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                "default": ""},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_on", "description": "duration of pulse in ms", "default": 50},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_off", "description": "resting time between pulses in ms", "default": 50},
        ]
    }
    _HardwareInterfaceClass = OptogeneticHardware

    def __init__(
        self, *args, interval=120, **kwargs
    ):
        self._interval = interval * 1000
        super(OptogeneticStimulatorSystematic, self).__init__(*args, **kwargs)
        self._t0 = 0

    def _decide(self):
        out, dic = super(OptogeneticStimulatorSystematic, self)._decide()
        dic["pulse_on"] = self._pulse_on
        dic["pulse_off"] = self._pulse_off
        return out, dic



import numpy as np
from ethoscope.trackers.adaptive_bg_tracker import AdaptiveBGModel
from ethoscope.core.roi import ROI 
from ethoscope.hardware.interfaces.interfaces import HardwareConnection
import argparse

def get_parser():

    parser = argparse.ArgumentParser()
    parser.add_argument("--rois", nargs="+", type=int)
    return parser

def never_moving():
    return False


def setup_roi(idx):

    hc = HardwareConnection(OptogeneticStimulator._HardwareInterfaceClass, do_warm_up=False)

    sd = OptogeneticStimulator(
            hc,
            velocity_correction_coef=0.01,
            min_inactive_time=10,  # s
            pulse_duration = 1000,  #ms
            date_range="",
            pulse_on=50,
            pulse_off=50,
    )
    sd._has_moved = never_moving
    sd._t0 = 0

    roi = ROI(polygon=np.array([[0, 10], [10, 10], [10, 0], [0, 0]]), idx=idx)
    tracker = AdaptiveBGModel(roi=roi)
    tracker._last_time_point = 30000 #ms

    sd.bind_tracker(tracker)
    return sd

def main():

    args = get_parser().parse_args()

    print("Applying")
    sds = [setup_roi(idx) for idx in args.rois]

    for sd in sds:
        interact, result = sd.apply()
        print(interact)
        print(result)
    
    for sd in sds:
        hc = sd._hardware_connection
        while len(hc._instructions) != 0:
            time.sleep(.1)    
        hc.stop()
    
if __name__ == "__main__":
    main()
