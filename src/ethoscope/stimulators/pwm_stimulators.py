import logging
from ethoscope.stimulators.stimulators import BaseStimulator, HasInteractedVariable
from ethoscope.hardware.interfaces.interfaces import  DefaultInterface
from ethoscope.hardware.interfaces.sleep_depriver_interface import SleepDepriverInterface, SleepDepriverInterfaceCR
from ethoscope.hardware.interfaces.optomotor import OptoMotor, SleepDepriver, PWMSleepDepriver
# from ethoscope.hardware.interfaces.interfaces import HardwareConnection, DynamicPWMHardwareConnection

from ethoscope.stimulators.sleep_depriver_stimulators import RobustSleepDepriver
import numpy as np
import random
import time
import logging
import sys
if sys.version_info[0] < 3: 
    from StringIO import StringIO
else:
    from io import StringIO

logger=logging.getLogger(__name__)

def merge_asof(d, x):
    """

    """
    hits = np.where(np.array(d["time"]) < x)[0]
    if len(hits)>=1:
        hit = hits[-1]
    else:
        hit = 0
    
    result = {k: [d[k][hit]] for k in d}
    return result


class PWMChecker:
    """
    Share a notion of last_time and last_val across different stimulators so that
    decision about a global pwm value is not overriden by each stimulator,
    but instead only one of them is used.
    This assumes that all stimulators would decide to update the pwm value to the same value at the same time

    """
    
    def __init__(self):
        self._interface=None
        self.last_time=None
        self.last_val=None
        self.min_time_pwm=None
        self.pwm_program=None


    def update(self, t, val):
        # only update the PWM via comm with the serial monitor if
        # 1) t is a new time (i.e. not the same as the last reference time whose pwm value was sent)
        # 2) val is a new value (i.e. if the active pwm value in the board is the same as this, dont do anything)
        #  2) is a bit of an edge case because typically you wouldn't have two values consecutively in the table of time-pwm
        if (self.last_time is None or self.last_time < t) and (self.last_val is None or self.last_val!=val):
            self._interface.set_pwm(val)
            self.last_time=t
            self.last_val=val


# class RandomPWMRobustSleepDepriver(RobustSleepDepriver):
#     _description = {"overview": "Stimulator with motor that experience a variable PWM",
#                 "arguments": [
#                     {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
#                                 {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken(s)","default":10},
#                                 {"type": "number", "min": 10, "max": 10000 , "step": 10, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
#                                 {"type": "str", "name": "date_range",
#                                  "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
#                                  "default": ""},
#                                 {"type": "number", "min": 1, "max": 720 , "step": 1, "name": "min_time_pwm", "description": "For how long to keep the pwm value, in mins", "default": 1},
#                                  {"type": "str", "name": "strategy",
#                                  "description": "PWM value selection strategy",
#                                  "default": "random"},
#                                ]}

#     _HardwareInterfaceClass = PWMSleepDepriver
#     min_time_pwm = 1        # min
#     current_pwm = None
 
#     def __init__(self, hardware_connection, checker, *args, min_time_pwm=1, strategy = "random", **kwargs):
#         super(RandomPWMRobustSleepDepriver, self).__init__(hardware_connection, *args, **kwargs)
#         hardware_connection.min_time_pwm = min_time_pwm
#         hardware_connection.strategy = strategy
#         self.connect_checker(checker)




# {"type": "bigtext", "name": "pwm_program", "description": "CSV style info for what PWM value to use for a given timepoint from start of SD. Time in min", "default": "time,pwm\n0,255"},
class PWMSleepDepriverStimulator(RobustSleepDepriver):
    _description = {"overview": "Stimulator with motor that experience a variable PWM and timings can be programmed by user",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken(s)","default":10},
            {"type": "number", "min": 10, "max": 10000 , "step": 10, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
            {
                "type": "str", "name": "date_range",
                "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                "default": ""
            },
            {
                "type": "bigtext", "name": "pwm_program",
                "description": "CSV style info for what PWM value to use for a given timepoint from start of SD. Time in min",
                "default": "time,pwm\n0,255"
            },
        ]}

    # Found in optomotor.py - has instructions to send Arduino serial command with set_pwm
    _HardwareInterfaceClass = PWMSleepDepriver
    current_pwm_val=None

    def __init__(self, hardware_connection, checker, *args, pwm_program = "time,pwm\n0,255", **kwargs):
        # UserPlan is the CSV type of string that the user provides with timepoint and PWM val
        # we then convert it to a dataframe, assuming separators are commas
        super(PWMSleepDepriverStimulator, self).__init__(hardware_connection, *args, **kwargs)
        self.pwm_program=self.parse_pwm_program(pwm_program)
        self.connect_checker(checker)
    

    @staticmethod
    def parse_pwm_program(pwm_program):

        with StringIO(pwm_program) as handle:
            csvfile = csv.reader(handle)
            data=list(iter(csvfile))

        pwm_program={k: [] for k in data[0]}
        for i in range(1, len(data)):
            for j, k in enumerate(data[0]):
                pwm_program[k].append(data[i][j])

        for k in pwm_program:
            pwm_program[k]=np.array(pwm_program[k])

       
        # TODO check if any() is same as ().any()#
        # check that the user passed a table which is sorted by time
        if (pwm_program["time"].diff() < 0).any():
            raise Exception("Time table is not chronologically ordered")
        
        if pwm_program["time"].iloc[0]!=0:
            raise Exception("""
                            Please pass always in the first row the pwm value desired at time 0" \
                            i.e. start your table with time=0
                            """
            )

        if pwm_program.shape[0] > 1 and (pwm_program["pwm"].diff() == 0).any():
            logger.warning("You passed two or more consecutive pwm values that are the same")
        return pwm_program
    

    # Create "slave" object for all the motor objects to use - should contain all PWM control methods
    @classmethod
    def get_args(cls):
        checker=PWMChecker()
        return [checker]


    def get_time_since_sd(self):
        t0, t1=self._scheduler._parse_date_range()
        if time.time()-t1>0:
            raise Exception("SD should have finished")
            
        sec_since_sd_start = time.time() - t0
        sec_since_sd_start/=60

        return sec_since_sd_start
    
    
    def _decide_pwm_change(self):
        """
        Return matched time in the reference table and
        corresponding pwm value that should be active
        """
        # Check which idx val current time would point to
        try:
            t = self.get_time_since_sd()

            row = merge_asof(self.checker.pwm_program, t)

            val=row["pwm"][0]
            t=row["time"][0]

        except Exception as error:
            logger.error(error)
            t = None
            val = 0

        return t, val
        

    # Send command via interface to actally change PWM value to what was decided
    def _decide(self, *args, **kwargs):
        #returns tuple true/false and dict
        out=super(PWMSleepDepriverStimulator, self)._decide(*args, **kwargs)
        t, val=self._decide_pwm_change()
        self.checker.update(t, val)
        return out
    

    def connect_checker(self, checker):
        self.checker=checker
        #if self.checker.min_time_pwm is None:
        #    self.checker.min_time_pwm=self.min_time_pwm
        if self.checker._interface is None:
           self.checker._interface=self._hardware_connection._interface
        if self.checker.pwm_program is None:
            self.checker.pwm_program=self.pwm_program

    # Create "slave" object for all the motor objects to use - should contain all PWM control methods
    @classmethod
    def get_args(cls):
        """
        Called in _set_tracking_from_scratch         
        """
        checker=PWMChecker()
        return [checker]
    


class RandomPWMSleepDepriverStimulator(PWMSleepDepriverStimulator):

    MINVAL = 30

    _description = {"overview": "Stimulator with motor that experience a variable PWM and timings can be programmed by user",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken(s)","default":10},
            {"type": "number", "min": 10, "max": 10000 , "step": 10, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
            {"type": "str", "name": "date_range",
                "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                "default": ""},
            {"type": "number", "min": 1, "max": 720 , "step": 1, "name": "min_time_pwm", "description": "For how long to keep the pwm value, in mins", "default": 1},
            ]}

    def __init__(self, *args, min_time_pwm=1, **kwargs):
        
        t0, t1=self._scheduler._parse_date_range()

        duration=(t1-t0) / 60 # mins
        
        number_of_intervals=int(duration//min_time_pwm)

        pwm_program=[
            (str(i*min_time_pwm), str(self.generate_random_pwm()))
            for i in range(number_of_intervals)
        ]
        
        pwm_program=[",".join(row) for row in pwm_program]
        pwm_program="\n".join(pwm_program)
    
        pwm_program="time,pwm\n" + pwm_program
        super(RandomPWMSleepDepriverStimulator, self).__init__(*args, pwm_program=pwm_program, min_time_pwm=min_time_pwm, **kwargs)


    def generate_random_pwm(self):
        value = int(random.random() * 255)
        value = max(value,self.MINVAL)
        return value
