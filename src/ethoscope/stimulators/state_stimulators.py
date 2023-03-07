import logging

import numpy as np

from ethoscope.stimulators.sleep_depriver_stimulators import RobustSleepDepriver
from ethoscope.hardware.interfaces.optomotor import OptoMotor
from ethoscope.stimulators.stimulators import BaseStimulator, HasInteractedVariable
from ethoscope.hardware.interfaces.optogenetics import OptogeneticHardware
from ethoscope.hardware.interfaces.interfaces import HardwareConnection 

from ethoscope.core.roi import ROI

class StaticStimulator(RobustSleepDepriver):
    """
    A stimulator that provides a different stimulus
    depending on the current state of the animal, for as long as needed
    """
    
    _state = None
    _HardwareInterfaceClass = OptogeneticHardware

    def __init__(self, *args, pulse_on=50, pulse_off=50, min_time=10, **kwargs):

        if not "min_inactive_time" in kwargs:
            kwargs["min_inactive_time"] = min_time

        program = kwargs.pop("program", "")
        self._pulse_on=pulse_on
        self._pulse_off=pulse_off
        super().__init__(*args, **kwargs)
        self._time_threshold_ms = self._inactivity_time_threshold_ms


    def _decide(self):

        dic={}
        dic["duration"] = self._pulse_duration
        dic["pulse_on"] = self._pulse_on
        dic["pulse_off"] = self._pulse_off
        if self._tracker._roi.idx not in self._roi_to_channel:
            return HasInteractedVariable(False), {}

        dic["channel"] = self._roi_to_channel[self._tracker._roi.idx]

        now = self._tracker.last_time_point
        has_moved = self._has_moved()
        if self._t0 is None:
            self._t0 = now

        return self._decide_subclass(dic, now, has_moved)

        
        
class SleepStimulator(StaticStimulator):
    _state = "asleep"
    _HardwareInterfaceClass = OptogeneticHardware
    _description = {
        "overview": f"A stimulator to sleep deprive an animal using optogenetics. The animal will be stimulated for as long as it is {_state}",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_time", "description": "The minimal time after which an inactive animal is stimulated (s)","default":10},
            {"type": "number", "min": 10, "max": 10000 , "step": 10, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_on", "description": "duration of pulse in ms", "default": 50},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_off", "description": "resting time between pulses in ms", "default": 50},

        ]
    }

    def _decide_subclass(self, dic, now, has_moved):
        if has_moved:
            self._t0 = now
            return HasInteractedVariable(False), {}
        else:
            if float(now - self._t0) > self._time_threshold_ms:
                return HasInteractedVariable(True), dic
            else:
                return HasInteractedVariable(False), {}





class AwakeStimulator(StaticStimulator):
    _state = "awake"
    _HardwareInterfaceClass = OptogeneticHardware
    _description = {
        "overview": f"A stimulator to 'awake' deprive an animal using optogenetics. The animal will be stimulated for as long as it is {_state}. This class is a control of the SleepStimulator",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 0, "max": 3600*12, "step":1, "name": "min_time", "description": "The minimal time after which an active animal is stimulated (s)","default":0},
            {"type": "number", "min": 10, "max": 10000 , "step": 10, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},

            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_on", "description": "duration of pulse in ms", "default": 50},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_off", "description": "resting time between pulses in ms", "default": 50},

        ]
    }


    def _decide_subclass(self, dic, now, has_moved):
        if not has_moved:
            self._t0 = now
            logging.warning(f"Channel {dic['channel']} not moving")
            return HasInteractedVariable(False), {}
        else:
            if float(now - self._t0) > self._time_threshold_ms:
                logging.warning(f"""
                Channel {dic['channel']} has moved, stimulating because
                {now - self._t0} > {self._time_threshold_ms}
                """)
                return HasInteractedVariable(True), dic
            else:
                logging.warning(
                f"""
                Channel {dic['channel']} has moved, not stimulating because
                {now-self._t0} < {self._time_threshold_ms}
                """)
                return HasInteractedVariable(False), {}




if __name__ == "__main__":
    from ethoscope.trackers.adaptive_bg_tracker import AdaptiveBGModel

    def never_moving():
        return False

    def always_moving():
        return True
 
    def main():
        hc = HardwareConnection(AwakeStimulator._HardwareInterfaceClass, do_warm_up=False)
        idx_dict = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 12, 7: 14, 8:16, 9: 18, 10:20}

        for i in range(1, 11):
            #stim = AwakeStimulator(
            stim = SleepStimulator(
                hc,
                min_inactive_time=1000,
                velocity_correction_coef=0.01,
                pulse_duration=1000,
                date_range="",
                pulse_on=50,
                pulse_off=50,
            )
    
            #stim._has_moved = always_moving 
            stim._has_moved = never_moving 
            stim._t0 = 0
            idx = idx_dict[i]
            roi = ROI(polygon=np.array([[0, 10], [10, 10], [10, 0], [0, 0]]), idx=idx)
            tracker = AdaptiveBGModel(roi=roi)
            tracker._last_time_point = 30000 #ms
            stim.bind_tracker(tracker)
            interact, result = stim.apply()

    main()