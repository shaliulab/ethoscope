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

    def __init__(self, *args, pulse_on=50, pulse_off=50, **kwargs):

        program = kwargs.pop("program", "")
        self._pulse_on=pulse_on
        self._pulse_off=pulse_off
        super().__init__(*args, **kwargs)

    def _decide(self):

        dic={}
        dic["duration"] = self._pulse_duration
        dic["pulse_on"] = self._pulse_on
        dic["pulse_off"] = self._pulse_off
        if self._tracker._roi.idx not in self._roi_to_channel:
            return HasInteractedVariable(False), {}

        dic["channel"] = self._roi_to_channel[self._tracker._roi.idx]
        
        
        has_moved = self._has_moved()
        if has_moved and self._state == "awake":
            return HasInteractedVariable(True), dic
        elif not has_moved and self._state == "asleep":
            return HasInteractedVariable(True), dic
        else:
            return HasInteractedVariable(False), {}
        
        
class SleepStimulator(StaticStimulator):
    _state = "asleep"
    _HardwareInterfaceClass = OptogeneticHardware
    _description = {
        "overview": "A stimulator to sleep deprive an animal using optogenetics. The animal will be stimulated for as long as it is asleep",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 10, "max": 10000 , "step": 10, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_on", "description": "duration of pulse in ms", "default": 50},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_off", "description": "resting time between pulses in ms", "default": 50},

        ]
    }



class AwakeStimulator(StaticStimulator):
    _state = "awake"
    _HardwareInterfaceClass = OptogeneticHardware
    _description = {
        "overview": "A stimulator to sleep deprive an animal using optogenetics. The animal will be stimulated for as long as it is awake",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 10, "max": 10000 , "step": 10, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_on", "description": "duration of pulse in ms", "default": 50},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_off", "description": "resting time between pulses in ms", "default": 50},

        ]
    }




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
