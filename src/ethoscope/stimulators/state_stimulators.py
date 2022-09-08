from ethoscope.stimulators.sleep_depriver_stimulators import RobustSleepDepriver
from ethoscope.hardware.interfaces.optomotor import OptoMotor
from ethoscope.stimulators.stimulators import BaseStimulator, HasInteractedVariable


class StaticStimulator(RobustSleepDepriver):
    """
    A stimulator that provides a different stimulus
    depending on the current state of the animal, for as long as needed
    """
    
    _state = None
    _description = {
        "overview": "A stimulator to sleep deprive an animal using gear motors. See https://github.com/gilestrolab/ethoscope_hardware/tree/master/modules/gear_motor_sleep_depriver. NOTE: Use  this class if you are using a SD module using the new PCB (Printed Circuit Board)",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken(s)","default":10},
            {"type": "number", "min": 10, "max": 10000 , "step": 10, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_on", "description": "duration of pulse in ms", "default": 50},
            {"type": "number", "min": 20, "max": 1000 , "step": 1, "name": "pulse_off", "description": "resting time between pulses in ms", "default": 50},

        ]
    }

    _HardwareInterfaceClass = OptoMotor

    def __init__(self, *args, pulse_on=50, pulse_off=50, **kwargs):

        program = kwargs.pop("program", "")
        self._pulse_on=pulse_on
        self._pulse_off=pulse_off
        super().__init__(*args, **kwargs)
        self._scheduler = self._schedulerClass(kwargs["date_range"], program=program)

    def _decide(self):

        dic={}
        dic["duration"] = self._pulse_duration
        dic["pulse_on"] = self._pulse_on
        dic["pulse_off"] = self._pulse_off
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

class AwakeStimulator(StaticStimulator):
    _state = "awake"
