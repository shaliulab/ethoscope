from ethoscope.stimulators.sleep_depriver_stimulators import MiddleCrossingStimulator
from ethoscope.hardware.interfaces.optomotor import OptoMotor, SleepDepriver


class OptoMidlineCrossStimulator (MiddleCrossingStimulator):
    _description = {"overview": "A stimulator to shine light when animals cross the midline",
                    "arguments": [
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":0.01, "name": "p", "description": "the probability to move the tube when a beam cross was detected","default":1.0},
                                    {"type": "date_range", "name": "date_range",
                                     "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                                     "default": ""}
                                   ]}
    _HardwareInterfaceClass = OptoMotor
    _roi_to_channel = {
        1: 1,
        3: 3,
        5: 5,
        7: 7,
        9: 9,
        12: 23,
        14: 21,
        16: 19,
        18: 17,
        20: 15
    }





class MotoMidlineCrossStimulator (MiddleCrossingStimulator):
    _description = {"overview": "A stimulator to turn gear motor when animals cross the midline",
                    "arguments": [
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":0.01, "name": "p", "description": "the probability to move the tube when a beam cross was detected","default":1.0},
                                    {"type": "number", "min": 0.0, "max": 300, "step":1, "name": "refractory_period", "description": "the minimum time between stimuli in seconds","default":5.0},
                                    {"type": "date_range", "name": "date_range",
                                     "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                                     "default": ""}
                                   ]}
    _HardwareInterfaceClass = OptoMotor
    _roi_to_channel = {
        1: 0,
        3: 2,
        5: 4,
        7: 6,
        9: 8,
        12: 22,
        14: 20,
        16: 18,
        18: 16,
        20: 14
    }

    _duration = 2000


    def _decide(self):
        has_interacted, dic = super(MotoMidlineCrossStimulator, self)._decide()
        dic["duration"] = self._duration
        return has_interacted, dic

class RobustMotoMidlineCrossStimulator (MotoMidlineCrossStimulator):
    _description = {"overview": "A stimulator to turn gear motor when animals cross the midline using the new PCB design",
                   "arguments": [
                                   {"type": "number", "min": 0.0, "max": 1.0, "step":0.01, "name": "p", "description": "the probability to move the tube when a beam cross was detected","default":1.0},
                                   {"type": "number", "min": 0, "max": 10000, "step":100, "name": "duration", "description": "time pulse duration","default": 100},
                                   {"type": "number", "min": 0.0, "max": 300.0, "step":1.0, "name": "refractory_period", "description": "the minimum time between stimuli in seconds","default": 5.0},
                                   {"type": "date_range", "name": "date_range",
                                    "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                                    "default": ""}
                                  ]}

    _HardwareInterfaceClass = SleepDepriver
    _roi_to_channel = {
        1: 1,
        3: 3,
        5: 5,
        7: 7,
        9: 9,
        12: 11,
        14: 13,
        16: 15,
        18: 17,
        20: 19
    }
 
    _duration = 100
 
    def __init__(self, *args, duration=100, **kwargs):
        self._duration = duration
        super(RobustMotoMidlineCrossStimulator, self).__init__(*args, **kwargs)
 
