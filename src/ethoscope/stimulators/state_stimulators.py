import logging
import time
from typing import Any

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

    Arguments:
        min_time: minimum amount of time in the state before the stimulator responds to it (s)
        min_time_not: minimum amount of time in the opposite (not) state before the stimulator responds to it (s)
        **kwargs: other arguments to RobustSleepDepriver
    """

    _state = None
    _HardwareInterfaceClass = StaticOptogeneticHardware

    def __init__(self, *args, min_time=10, min_time_not=0, **kwargs):

        assert min_time > 0 # we need a refractory period to prevent hardware malfunction?

        kwargs["min_inactive_time"] = min_time

        super().__init__(*args, **kwargs)
        self._time_threshold_ms = self._inactivity_time_threshold_ms
        if self._state == "awake":
            self._time_threshold_not_ms = min_time_not*1000
        elif self._state == "asleep":
            self._time_threshold_not_ms=0

        self._last_time_in_stimulating_state = None


    def _prepare(self):
        dic={}
        dic["channel"] = self._roi_to_channel[self._tracker._roi.idx]
        dic["duration"]=self._pulse_duration

        now = self._tracker.last_time_point
        has_moved = self._has_moved()

        return dic, now, has_moved


class MaskStimulationInterruptionsMixin:
    """
    Mixin that masks brief interruptions of the stimulating state
    i.e. you ignore brief bouts of the opposite state
    (i.e., short 'not-state' bouts), implementing a hysteresis on has_moved.
    If _time_threshold_not_ms = 0, no mask is applied, this is good in the case of the sleep stimulator
    because you dont want to ignore "brief" bouts of activity
    But you need a mask (_time_threshold_not_ms > 0) in the awake stimulator
    to mask events when the fly does not move from one frame to next
    even if it is moving in other neighboring frames
    """

    def _prepare(self):
        dic, now, has_moved = super()._prepare()

        if self._state not in ("awake", "asleep"):
            raise ValueError(f"_state must be 'awake' or 'asleep', got {self._state!r}")

        # Initialize reference time on first call
        if self._last_time_in_stimulating_state is None:
            self._last_time_in_stimulating_state = now

        #   awake  -> has_moved == True
        #   asleep -> has_moved == False
        if self._state == "awake":
            in_stim_state = has_moved
        elif self.state_=="asleep":
            in_stim_state = not has_moved

        if in_stim_state:
            self._last_time_in_stimulating_state = now
            return dic, now, has_moved

        else:
            # Not in stimulating state; potentially mask short interruptions
            if (now - self._last_time_in_stimulating_state) < self._time_threshold_not_ms:
                logging.warning(
                    "Masking short %s bout",
                    "quiescence" if self._state == "awake" else "moving",
                )
                if self._state == "awake":
                    # pretend the fly is still moving although it is not (mask)
                    masked_has_moved = True
                elif self._state == "asleep":
                    # pretend the fly is still not moving although it has started moving (mask)
                    masked_has_moved = False
                return dic, now, masked_has_moved

            else:
                return dic, now, has_moved



class StaticSleepStimulator(MaskStimulationInterruptionsMixin, StateStimulator):
    """
    A stimulator that delivers the stimulus for as long as the fly is asleep

    Arguments:
        min_time: minimum amount of time asleep before the stimulator responds to it (s)
        min_time_not: minimum amount of time awake before the stimulator responds to it (s)
        **kwargs: other arguments to RobustSleepDepriver
    """

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

    def __init__(self, *args, **kwargs):

        # t0 = last time that the stimulator ran _decide
        # None if in the last step it sent a stimulus
        self._t0 = None
        self._tracker=None
        super(StaticSleepStimulator, self).__init__(*args, **kwargs)

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
            return HasInteractedVariable(-1), dic
        else:
            if float(now - self._t0) > self._time_threshold_ms:
                logging.warning("First pulse")
                self._t0 = None
                dic["turnon"]=True
                return HasInteractedVariable(1), dic
            else:
                logging.warning("Not enough time in state")
                return HasInteractedVariable(0), {}


class StaticAwakeStimulator(MaskStimulationInterruptionsMixin, StateStimulator):
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

    """
    A stimulator that delivers the stimulus for as long as the fly is awake

    Arguments:
        min_time: minimum amount of time awake before the stimulator responds to it (s)
        min_time_not: minimum amount of time asleep before the stimulator responds to it (s)
        **kwargs: other arguments to RobustSleepDepriver
    """
    def __init__(self, *args, **kwargs):

        # t0 = last time that the stimulator ran _decide
        # None if in the last step it sent a stimulus
        self._t0 = None
        self._tracker=None
        super(StaticAwakeStimulator, self).__init__(*args, **kwargs)

    def _decide(self, *args, **kwargs):
        if self._tracker._roi.idx not in self._roi_to_channel:
            return HasInteractedVariable(0), {}

        dic, now, has_moved = self._prepare(*args, **kwargs)
        if self._t0 is None:
            self._t0 = now

        if not has_moved:
            self._t0 = now
            logging.warning("Pulse needs to stop ASAP")
            # TODO Here we could deliver a STOP signal which is not yet implemented in Arduino
            dic["turnon"]=False
            return HasInteractedVariable(-1), dic
        else:
            if float(now - self._t0) > self._time_threshold_ms:
                logging.warning("First pulse")
                self._t0 = None
                dic["turnon"]=True
                return HasInteractedVariable(1), dic
            else:
                logging.warning("Not enough time in state")
                return HasInteractedVariable(0), {}


class StatePulseStimulator(StateStimulator):
    """
    Like the StateStimulator but with a frequency pulse at a given frequency
    """

    _HardwareInterfaceClass = OptogeneticHardware

    def __init__(self, *args, pulse_on=50, pulse_off=50, **kwargs):
        super(StatePulseStimulator, self).__init__(*args, **kwargs)
        self._pulse_on = pulse_on
        self._pulse_off = pulse_off

    def _prepare(self, *args, **kwargs):
        dic, now, has_moved = super(StatePulseStimulator, self)._prepare(*args, **kwargs)
        dic["pulse_on"]=self._pulse_on
        dic["pulse_off"]=self._pulse_off
        return dic, now, has_moved


class PulseSleepStimulator(MaskStimulationInterruptionsMixin, StatePulseStimulator):
    _state = "asleep"
    _HardwareInterfaceClass = OptogeneticHardware
    _description = {
        "overview": f"A stimulator to sleep deprive an animal using optogenetics. The animal will be stimulated for as long as it is {_state}",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_time", "description": "The minimal time after which an inactive animal is stimulated (s)","default":10},
            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
            {"type": "number", "min": 0, "max": 100000 , "step": 1, "name": "pulse_on", "description": "duration of pulse in ms. Set pulse_on to 1000 and pulse_off to 0 for static", "default": 50},
            {"type": "number", "min": 0, "max": 100000 , "step": 1, "name": "pulse_off", "description": "resting time between pulses in ms. Set pulse_on to 1000 and pulse_off to 0 for static", "default": 50},
            {"type": "number", "min": 500, "max": 10000 , "step": 50, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
        ]
    }

    def __init__(self, *args, **kwargs):

        # t0 = last time that the stimulator ran _decide
        # None if in the last step it sent a stimulus
        self._t0 = None
        self._tracker=None
        super(PulseSleepStimulator, self).__init__(*args, **kwargs)

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
            return HasInteractedVariable(-1), dic
        else:
            if float(now - self._t0) > self._time_threshold_ms:
                logging.warning("First pulse")
                self._t0 = None
                dic["turnon"] = True
                return HasInteractedVariable(1), dic
            else:
                logging.warning("Not enough time")
                return HasInteractedVariable(0), {}



class PulseAwakeStimulator(MaskStimulationInterruptionsMixin, StatePulseStimulator):
    _state = "awake"
    _HardwareInterfaceClass = OptogeneticHardware
    _description = {
        "overview": f"A stimulator to awake deprive an animal using optogenetics. The animal will be stimulated for as long as it is {_state}",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_time", "description": "The minimal time after which an active animal is stimulated (s)","default":5},
            {"type": "number", "min": 0, "max": 3600*12, "step":1, "name": "min_time_not", "description": "The minimal time after which an inactive animal is not stimulated anymore (s)","default":5},
            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
            {"type": "number", "min": 0, "max": 100000 , "step": 1, "name": "pulse_on", "description": "duration of pulse in ms. Set pulse_on to 1000 and pulse_off to 0 for static", "default": 50},
            {"type": "number", "min": 0, "max": 100000 , "step": 1, "name": "pulse_off", "description": "resting time between pulses in ms. Set pulse_on to 1000 and pulse_off to 0 for static", "default": 50},
            {"type": "number", "min": 500, "max": 10000 , "step": 50, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
        ]
    }

    def __init__(self, *args, min_time_not=10, **kwargs):

        # t0 = last time that the stimulator ran _decide
        # None if in the last step it sent a stimulus
        self._t0 = None
        self._tracker=None

        assert min_time_not > 0, """
          Please enter a non-zero min_time_not
          to prevent the stimulator to not turn on
          the lights because of brief inactivity.
          Only if the inactivity is continuous for > min_time_not seconds
          will the stimulator stop the lights
        """
        super(PulseAwakeStimulator, self).__init__(*args, **kwargs)

    def _decide(self, *args, **kwargs):
        if self._tracker._roi.idx not in self._roi_to_channel:
            return HasInteractedVariable(0), {}


        dic, now, has_moved = self._prepare(*args, **kwargs)

        if self._t0 is None:
            self._t0 = now


        logging.warning("%s : %s", now, has_moved)

        if not has_moved:
            self._t0 = now
            dic["turnon"] = False
            return HasInteractedVariable(-1), dic
        else:
            diff = float(now - self._t0)
            if diff  > self._time_threshold_ms:
                logging.warning("First pulse")
                self._t0 = None
                dic["turnon"] = True
                return HasInteractedVariable(1), dic
            else:
                logging.warning("Not enough time: %s", diff)
                return HasInteractedVariable(0), {}


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
