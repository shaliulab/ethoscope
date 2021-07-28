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

    _description = {"overview": "A stimulator to sleep deprive an animal using gear motors. See https://github.com/gilestrolab/ethoscope_hardware/tree/master/modules/gear_motor_sleep_depriver. NOTE: Use this class if you want to use different pulse durations at different ZT (probably longer duration at later ZT).",
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
                                 "description": """
                                 A scheduling program to SD flies with different pulse duration throughout the experiment.
                                 Format the input string as follows
                                 HOUR_SINCE_START > PULSE_DURATION;HOUR_SINCE_START > PULSE_DURATION;HOUR_SINCE_START > PULSE_DURATION
                                 example:
                                 0 > 500; 6 > 1000; 12 > 1500; 18 > 2000
                                 will use 500 ms for the first 6 hours, 1000 for the next 6, 1500 for the next 6 and 2000 for the remaining ones
                                 """,
                                 "default": ""}

                               ]}

    _schedulerClass = SegmentedScheduler
    _HardwareInterfaceClass = SleepDepriver
    _duration = 500

    def __init__(self, *args, **kwargs):

        program = kwargs.pop("program", "")
        super().__init__(*args, **kwargs)
        self._scheduler = self._schedulerClass(kwargs["date_range"], program=program)

    def _decide(self, **kwargs):
        
        out, dic = super()._decide(**kwargs)

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


if __name__ == "__main__":
    print(SegmentedStimulator._HardwareInterfaceClass)
    
