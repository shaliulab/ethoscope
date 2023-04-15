import logging
import time

import numpy as np

from ethoscope.stimulators.sleep_depriver_stimulators import RobustSleepDepriver
from ethoscope.hardware.interfaces.optomotor import OptoMotor
from ethoscope.stimulators.stimulators import BaseStimulator, HasInteractedVariable
from ethoscope.hardware.interfaces.optogenetics import (
    OptogeneticHardware,
    StaticOptogeneticHardware,
    IndefiniteOptogeneticHardware
)
from ethoscope.hardware.interfaces.interfaces import HardwareConnection 

from ethoscope.core.roi import ROI

class StateStimulator(RobustSleepDepriver):
    """
    A stimulator that provides a different stimulus
    depending on the current state of the animal, for as long as needed
    """
    
    _state = None
    _HardwareInterfaceClass = StaticOptogeneticHardware

    def __init__(self, *args, min_time=10, min_time_not=0, **kwargs):

        if not "min_inactive_time" in kwargs:
            kwargs["min_inactive_time"] = min_time

        program = kwargs.pop("program", "")
        super().__init__(*args, **kwargs)
        self._time_threshold_ms = self._inactivity_time_threshold_ms
        self._time_threshold_not_ms = min_time_not*1000

        self._last_time_in_stimulating_state = 0


    def _prepare(self):
        dic={}
        dic["channel"] = self._roi_to_channel[self._tracker._roi.idx]

        now = self._tracker.last_time_point
        has_moved = self._has_moved()
       
        return dic, now, has_moved


class MaskStimulationInterruptions:

    def _prepare(self):
        dic, now, has_moved = super(StaticSleepStimulator, self)._prepare()
        
        if self._state == "awake":
            if has_moved:
                # has moved is True
                self._last_time_in_stimulating_state = now
                return dic, now, has_moved
            elif (now - self._last_time_in_stimulating_state) < self._time_threshold_not_ms:
                # has moved is False but we
                # pretend it's True if it's been False for a very short time
                return dic, now, True 
            else:
                # has moved is False
                return dic, now, has_moved
        elif self._state == "asleep":
            if not has_moved:
                # has moved is False
                self._last_time_in_stimulating_state = now
                return dic, now, has_moved
            elif (now - self._last_time_in_stimulating_state) < self._time_threshold_not_ms:
                # has moved is True but we
                # pretend it's False if it's been True for a very short time
                return dic, now, False 
            else:
                # has moved is True
                return dic, now, has_moved

class StaticSleepStimulator(MaskStimulationInterruptions, StateStimulator):
    _state = "asleep"
    _HardwareInterfaceClass = StaticOptogeneticHardware
    _description = {
        "overview": f"A stimulator to sleep deprive an animal using optogenetics. The animal will be stimulated for as long as it is {_state}",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_time", "description": "The minimal time after which an inactive animal is stimulated (s)","default":10},
            {"type": "number", "min": 0, "max": 3600*12, "step":1, "name": "min_time_not", "description": "The minimal time after which an active animal is not stimulated anymore (s)","default":0},
            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
        ]
    }
        
    def _decide(self, *args, **kwargs):
        if self._tracker._roi.idx not in self._roi_to_channel:
            return HasInteractedVariable(False), {}

        dic, now, has_moved = self._prepare(*args, **kwargs)

        if self._t0 is None:
            self._t0 = now

        if has_moved:
            self._t0 = now
            logging.warning("Pulse needs to stop ASAP")
            dic["turnon"]=False
            return HasInteractedVariable(True), dic
        else:
            if float(now - self._t0) > self._time_threshold_ms:
                logging.warning("First pulse")
                self._t0 = None
                dic["turnon"]=True
                return HasInteractedVariable(True), dic
            else:
                logging.warning("Not enough time")
                return HasInteractedVariable(False), {}


class StaticAwakeStimulator(MaskStimulationInterruptions, StateStimulator):
    _state = "awake"
    _HardwareInterfaceClass = StaticOptogeneticHardware
    _description = {
        "overview": f"A stimulator to 'awake' deprive an animal using optogenetics. The animal will be stimulated for as long as it is {_state}. This class is a control of the SleepStimulator",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 0, "max": 3600*12, "step":1, "name": "min_time", "description": "The minimal time after which an active animal is stimulated (s)","default":0},
            {"type": "number", "min": 0, "max": 3600*12, "step":1, "name": "min_time_not", "description": "The minimal time after which an inactive animal is not stimulated anymore (s)","default":0},
            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
        ]
    }
        
    def _decide(self, *args, **kwargs):
        if self._tracker._roi.idx not in self._roi_to_channel:
            return HasInteractedVariable(False), {}

        dic, now, has_moved = self._prepare(*args, **kwargs)
        if self._t0 is None:
            self._t0 = now

        if not has_moved:
            self._t0 = now
            logging.warning("Pulse needs to stop ASAP")
            # TODO Here we could deliver a STOP signal which is not yet implemented in Arduino
            return HasInteractedVariable(True), {"channel": dic["channel"], "turnon": False}
        else:
            if float(now - self._t0) > self._time_threshold_ms:
                logging.warning("First pulse")
                self._t0 = None
                self._delivering = True
                return HasInteractedVariable(True), {"channel": dic["channel"], "turnon": True}
            else:
                logging.warning("Not enough time")
                return HasInteractedVariable(False), {}
    


class StatePulseStimulator(MaskStimulationInterruptions, StateStimulator):
    _HardwareInterfaceClass = IndefiniteOptogeneticHardware


    def __init__(self, *args, pulse_on=50, pulse_off=50, **kwargs):
        super(StatePulseStimulator, self).__init__(*args, **kwargs)
        self._pulse_on = pulse_on
        self._pulse_off = pulse_off

    def _prepare(self, *args, **kwargs):
        dic, now, has_moved = super(StatePulseStimulator, self)._prepare(*args, **kwargs)
        dic["pulse_on"]=self._pulse_on
        dic["pulse_off"]=self._pulse_off
        return dic, now, has_moved
    
   

class PulseSleepStimulator(StatePulseStimulator):
    _state = "asleep"
    _HardwareInterfaceClass = IndefiniteOptogeneticHardware
    _description = {
        "overview": f"A stimulator to sleep deprive an animal using optogenetics. The animal will be stimulated for as long as it is {_state}",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_time", "description": "The minimal time after which an inactive animal is stimulated (s)","default":10},
            {"type": "number", "min": 0, "max": 3600*12, "step":1, "name": "min_time_not", "description": "The minimal time after which an active animal is not stimulated anymore (s)","default":0},
            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
            {"type": "number", "min": 0, "max": 100000 , "step": 1, "name": "pulse_on", "description": "duration of pulse in ms. Set pulse_on to 1000 and pulse_off to 0 for static", "default": 50},
            {"type": "number", "min": 0, "max": 100000 , "step": 1, "name": "pulse_off", "description": "resting time between pulses in ms. Set pulse_on to 1000 and pulse_off to 0 for static", "default": 50},
        ]
    }

    def _decide(self, *args, **kwargs):
        if self._tracker._roi.idx not in self._roi_to_channel:
            return HasInteractedVariable(False), {}
        dic, now, has_moved = self._prepare(*args, **kwargs)

        if self._t0 is None:
            self._t0 = now

        if has_moved:
            self._t0 = now
            logging.warning("Pulse needs to stop ASAP")
            # TODO Here we could deliver a STOP signal which is not yet implemented in Arduino
            dic["turnon"] = False
            return HasInteractedVariable(True), dic
        else:
            if float(now - self._t0) > self._time_threshold_ms:
                logging.warning("First pulse")
                self._t0 = None
                self._delivering = True
                dic["turnon"] = True
                return HasInteractedVariable(True), dic
            else:
                logging.warning("Not enough time")
                return HasInteractedVariable(False), {}



class PulseAwakeStimulator(StatePulseStimulator):
    _state = "awake"
    _HardwareInterfaceClass = IndefiniteOptogeneticHardware
    _description = {
        "overview": f"A stimulator to awake deprive an animal using optogenetics. The animal will be stimulated for as long as it is {_state}",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_time", "description": "The minimal time after which an inactive animal is stimulated (s)","default":10},
            {"type": "number", "min": 0, "max": 3600*12, "step":1, "name": "min_time_not", "description": "The minimal time after which an inactive animal is not stimulated anymore (s)","default":0},
            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
            {"type": "number", "min": 0, "max": 100000 , "step": 1, "name": "pulse_on", "description": "duration of pulse in ms. Set pulse_on to 1000 and pulse_off to 0 for static", "default": 50},
            {"type": "number", "min": 0, "max": 100000 , "step": 1, "name": "pulse_off", "description": "resting time between pulses in ms. Set pulse_on to 1000 and pulse_off to 0 for static", "default": 50},
        ]
    }

    def _decide(self, *args, **kwargs):
        if self._tracker._roi.idx not in self._roi_to_channel:
            return HasInteractedVariable(False), {}
        
        
        dic, now, has_moved = self._prepare(*args, **kwargs)

        if self._t0 is None:
            self._t0 = now

        if not has_moved:
            self._t0 = now
            logging.warning("Pulse needs to stop ASAP")
            # TODO Here we could deliver a STOP signal which is not yet implemented in Arduino
            dic["turnon"] = False
            return HasInteractedVariable(True), dic
        else:
            if float(now - self._t0) > self._time_threshold_ms:
                logging.warning("First pulse")
                self._t0 = None
                self._delivering = True
                dic["turnon"] = True
                return HasInteractedVariable(True), dic
            else:
                logging.warning("Not enough time")
                return HasInteractedVariable(False), {}



if __name__ == "__main__":
    import sys

    hc = HardwareConnection(PulseSleepStimulator._HardwareInterfaceClass, do_warm_up=False, port="/dev/ttyACM0")
    stimulator = PulseSleepStimulator(
        hc,
        velocity_correction_coef=0.01,
        min_time = 10,
        min_time_not = 0,
        date_range = "",
        pulse_on=50,
        pulse_off=50,    
    )
    print(stimulator.__class__.__mro__)
    stimulator._hardware_connection.stop()
    sys.exit(0)

#     from ethoscope.trackers.adaptive_bg_tracker import AdaptiveBGModel

#     def never_moving():
#         return False

#     def always_moving():
#         return True
 
#     def main():
#         hc = HardwareConnection(AwakeStimulator._HardwareInterfaceClass, do_warm_up=False)
#         idx_dict = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 12, 7: 14, 8:16, 9: 18, 10:20}
#         stims = []

#         for i in range(1, 11):
#             #stim = AwakeStimulator(
#             stim = SleepStimulator(
#                 hc,
#                 min_inactive_time=1,
#                 velocity_correction_coef=0.01,
#                 date_range="",
#                 pulse_on=2000,
#                 pulse_off=0,
#             )
    
#             #stim._has_moved = always_moving 
#             stim._has_moved = never_moving 
#             stim._t0 = 0
#             idx = idx_dict[i]
#             roi = ROI(polygon=np.array([[0, 10], [10, 10], [10, 0], [0, 0]]), idx=idx)
#             tracker = AdaptiveBGModel(roi=roi)
#             tracker._last_time_point = 30000 #ms
#             stim.bind_tracker(tracker)
#             stims.append(stim)

#         i=0
#         while True:
#             time.sleep(.5)
#             for stim in stims:
#                 interact, result = stim.apply()
#                 stim._tracker._last_time_point += 500
#             i+=1

#     main()
