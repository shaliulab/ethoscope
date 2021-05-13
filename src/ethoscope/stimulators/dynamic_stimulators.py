import time
import numpy as np

from ethoscope.stimulators.sleep_depriver_stimulators import RobustSleepDepriver
from ethoscope.core.variables import BaseIntVariable
from ethoscope.utils.scheduler import Scheduler, SegmentedScheduler
from ethoscope.hardware.interfaces.optomotor import SleepDepriver


class InteractionDuration(BaseIntVariable):
    """
    Custom variable to save the duration of the stimulus / interaction sent to the animal
    """
    functional_type = "count"
    header_name = "duration"



class SegmentedStimulator(RobustSleepDepriver):
    """
    A stimulator that provides a different stimulus
    depending on the time elapsed since stimuli delivery started
    """

    _description = {"overview":
    """
    A stimulator to sleep deprive an animal using gear motors. See https://github.com/gilestrolab/ethoscope_hardware/tree/master/modules/gear_motor_sleep_depriver
    
    A custom pulse duration can be provided so a different stimulus duration is delivered throughout the experiment.
    This might better follow the arousal threshold change    
    """,
                "arguments": [
                    {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
                                {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken(s)","default":10},
                                {"type": "number", "min": 500, "max": 10000 , "step": 50, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 500},
                                #{"type": "number", "min": 0, "max": 1000, "step": 1, "name": "pulse_intensity",  "description": "intensity of stimulus 0-1000", "default": 1000},
                                {"type": "number", "min": 0, "max": 3, "step": 1, "name": "stimulus_type",  "description": "1 = opto, 2= moto", "default": 2},
                                {"type": "date_range", "name": "date_range",
                                 "description": "A date and time range in which the device will perform. See SegmentedScheduler help",
                                 "default": ""},
                                {"type": "str", "name": "program",
                                 "description": "A scheduling program to SD flies with different pulse duration throughout the experiment",
                                 "default": ""}

                               ]}

    _schedulerClass = SegmentedScheduler
    _HardwareInterfaceClass = SleepDepriver
    _duration = 500

    def __init__(self, *args, program="", **kwargs):
        super().__init__(*args, **kwargs)
        self._scheduler = self._schedulerClass(kwargs["date_range"], program=program)

    def _decide(self, *args, **kwargs):
        
        out, dic = super()._decide(*args, **kwargs)

        duration = self._scheduler.check_duration()
        if duration is None:
            pass
        else:
            dic["duration"] = duration

        return out, dic 


    def apply(self, *args, **kwargs):
        x = super().apply(*args, **kwargs)
        interaction, result = x
        if interaction:
            interaction_data = (interaction, InteractionDuration(result["duration"]))
        else:
            interaction_data = (interaction, InteractionDuration(0))
        return interaction_data, result



class DynamicStimulator(RobustSleepDepriver):
    _description = {"overview":
                """
                A stimulator to sleep deprive an animal using gear motors. See https://github.com/gilestrolab/ethoscope_hardware/tree/master/modules/gear_motor_sleep_depriver
                
                A dynamic pulse duration is delivered by the stimulator as a function of the animal's behavior.
                The stimulator infers the arousal threshold of the animal based on its behavior and adjusts the pulse duration accordingly.
                This might better follow the arousal threshold change    
                """,
                "arguments": [
                    {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
                                {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken(s)","default":10},
                                {"type": "number", "min": 0, "max": 10000 , "step": 50, "name": "min_pulse_duration", "description": "For how long to deliver the stimulus(ms), minimum", "default": 100},
                                {"type": "number", "min": 500, "max": 10000 , "step": 50, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 500},
                                {"type": "number", "min": 0, "max": 10000 , "step": 50, "name": "max_pulse_duration", "description": "For how long to deliver the stimulus(ms), maximum", "default": 2000},
                                {"type": "number", "min": 0, "max": 3, "step": 1, "name": "stimulus_type",  "description": "1 = opto, 2= moto", "default": 2},
                                {"type": "date_range", "name": "date_range",
                                 "description": "A date and time range in which the device will perform. See SegmentedScheduler help",
                                 "default": ""},
                               ]}
    
    _schedulerClass = Scheduler
    _HardwareInterfaceClass = SleepDepriver
    _duration = 500
    # exponential decay: the older an interaction is, the less it should matter
    # weight an interaction from 10 seconds ago with weight 1

    def __init__(self, *args, min_pulse_duration=100, max_pulse_duration=5000, **kwargs):
        
        super().__init__(*args, **kwargs)
        self._scale_factor = 1 / self._inactivity_time_threshold_ms

        self._arousal_threshold = 1
        self._min_pulse_duration = min_pulse_duration
        self._max_pulse_duration = max_pulse_duration
        self._HISTORY_LENGTH = 30*60*1000 # half an hour in ms
        self._MIN_HISTORY_LENGTH = 5*60*1000 # if the SD has been going on for less than this time, skip the dynamic computation
        # interactions that a fly with a standard arousability would have in half an hour (one / 2 mins)
        self._STANDARD_INTERACTIONS = self._HISTORY_LENGTH / (2*60*1000)
        self._last_n_interactions = self._STANDARD_INTERACTIONS
        self._history = np.array([])

    @property
    def arousal_threshold(self):
        self._arousal_threshold = self._last_n_interactions / self._STANDARD_INTERACTIONS
        return self._arousal_threshold

    @property
    def history_length(self):
        try:
            return self._history[-1] - self._history[0]
        except IndexError:
            return 0

  
    def register(self, t, duration=0):
        """
        If the interaction is non null (i.e. we are actually delivering)
        add this interaction to history
        Make sure the history is not too long
        """
        if duration == 0:
            return 0

        self._history = self._history[(t - self._history) < self._HISTORY_LENGTH]
        self._history = np.append(self._history, t)
        return 0


    def _decide(self, *args, **kwargs):

        out, dic = super()._decide(*args, **kwargs)

        duration = self.dynamic_duration(out, dic["duration"])
        if duration is None:
            pass
        else:
            dic["duration"] = duration

        dic["arousal_threshold"] = self.arousal_threshold

        return out, dic

    def dynamic_duration(self, duration, t=None):
        """
        Compute what the duration of the stimulus should be
        based on the history of previous stimuli
        """
        self.register(t, duration)
        n_interactions = len(self._history)

        if self.history_length < self._MIN_HISTORY_LENGTH:
            return duration

        if self.history_length < self._HISTORY_LENGTH:
            scalar = self._HISTORY_LENGTH / self.history_length
            n_interactions *= scalar

        self._last_n_interactions = n_interactions
        duration *= self.arousal_threshold
        duration = int(duration)

        duration = max(duration, self._min_pulse_duration)
        duration = min(duration, self._max_pulse_duration)
        return duration
        

    def apply(self, *args, **kwargs):
        x = super().apply(*args, **kwargs)
        interaction, result = x
        if interaction:
            interaction_data = (interaction, InteractionDuration(result["duration"]))
        else:
            interaction_data = (interaction, InteractionDuration(0))
        
        return interaction_data, result

        

if __name__ == "__main__":
    
    from ethoscope.hardware.interfaces.interfaces import HardwareConnection

    ds = DynamicStimulator(HardwareConnection(SleepDepriver, testing=True), min_inactive_time=10000)
    durations = []
    for i in range(60000, 60000*30, 60000):
        dur=ds.dynamic_duration(1000, i)
        durations.append(dur)

    durations.append("Switch")

    for i in range(60000*30, 120000*30, 120000):
        dur=ds.dynamic_duration(1000, i)
        durations.append(dur)

    durations.append("Switch")

    for i in range(120000*30, 180000*30, 15000):
        dur=ds.dynamic_duration(1000, i)
        durations.append(dur)

    print(durations)
