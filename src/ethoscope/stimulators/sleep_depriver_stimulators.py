'''
any new class added here need to be added to web_utils/control_thread.py too
'''

__author__ = 'quentin'


from ethoscope.stimulators.stimulators import BaseStimulator, HasInteractedVariable

from ethoscope.hardware.interfaces.interfaces import  DefaultInterface
from ethoscope.hardware.interfaces.sleep_depriver_interface import SleepDepriverInterface, SleepDepriverInterfaceCR
from ethoscope.hardware.interfaces.optomotor import OptoMotor, SleepDepriver


import random
import time
import logging

class IsMovingStimulator(BaseStimulator):
    _HardwareInterfaceClass = DefaultInterface

    def __init__(self, hardware_connection=None, velocity_correction_coef=3.0e-3, date_range = "", **kwargs):
        """
        class implementing an stimulator that decides whether an animal has moved though does nothing accordingly.
        :param hardware_connection: a default hardware interface object
        :param velocity_correction_coef: the correction coeeficient for computing velocity at various fps. Emirically defined. When greater than one, the animal is moving
        :type velocity_correction_coef: float
        """
        self._velocity_correction_coef = velocity_correction_coef
        self._last_active = 0
        super(IsMovingStimulator, self).__init__(hardware_connection, date_range)


    def _has_moved(self):

        positions = self._tracker.positions

        if len(positions ) <2 :
            return False


        if len(positions[-1]) != 1:
            raise Exception("This stimulator can only work with a single animal per ROI")
        tail_m = positions[-1][0]

        times = self._tracker.times
        last_time_for_position = times[-1]
        last_time = self._tracker.last_time_point

        # we assume no movement if the animal was not spotted
        if last_time != last_time_for_position:
            return False

        dt_s = abs(times[-1] - times[-2]) / 1000.0
        dist = 10.0 ** (tail_m["xy_dist_log10x1000"]/1000.0)
        logging.warning("Distance %s" % str(dist))
        velocity = dist / dt_s

        velocity_corrected = velocity * dt_s / self._velocity_correction_coef

        if velocity_corrected > 1.0:
            return True
        return False

    def _decide(self):

        has_moved = self._has_moved()

        t = self._tracker.times
        if  has_moved:# or xor_diff > self._xor_speed_threshold :
            self._last_active = t[-1]
            return HasInteractedVariable(False), {}
        return HasInteractedVariable(True), {}

class SleepDepStimulator(IsMovingStimulator):
    _description = {"overview": "A stimulator to sleep deprive an animal using servo motor. See http://todo/fixme.html",
                    "arguments": [
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef","default":3.0e-3},
                                    {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken","default":120},
                                    {"type": "date_range", "name": "date_range",
                                     "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                                     "default": ""},
                                   ]}

    _HardwareInterfaceClass = SleepDepriverInterface
    _roi_to_channel = {
            1:1,  3:2,  5:3,  7:4,  9:5,
            12:6, 14:7, 16:8, 18:9, 20:10
        }
    def __init__(self,
                 hardware_connection,
                 velocity_correction_coef=3.0e-3,
                 min_inactive_time=120,  #s
                 date_range=""
                 ):
        """
        A stimulator to control a sleep depriver module.

        :param hardware_connection: the sleep depriver module hardware interface
        :type hardware_connection: :class:`~ethoscope.hardware.interfaces.sleep_depriver_interface.SleepDepriverInterface`
        :param velocity_correction_coef:
        :type velocity_correction_coef: float
        :param min_inactive_time: the minimal time without motion after which an animal should be disturbed (in seconds)
        :type min_inactive_time: float
        :return:
        """

        self._inactivity_time_threshold_ms = min_inactive_time *1000 #so we use ms internally
        self._t0 = None
        
        super(SleepDepStimulator, self).__init__(hardware_connection, velocity_correction_coef, date_range=date_range)



    def _decide(self):
        roi_id= self._tracker._roi.idx
        now =  self._tracker.last_time_point

        try:
            channel = self._roi_to_channel[roi_id]
        except KeyError:
            return HasInteractedVariable(False), {}

        has_moved = self._has_moved()

        if self._t0 is None:
            self._t0 = now

        if not has_moved:
            if float(now - self._t0) > self._inactivity_time_threshold_ms:
                self._t0 = None
                return HasInteractedVariable(True), {"channel":channel}
        else:
            self._t0 = now
        return HasInteractedVariable(False), {}


class SleepDepStimulatorCR(SleepDepStimulator):
    _description = {"overview": "A stimulator to sleep deprive an animal using servo motor in Continous Rotation mode. See http://todo/fixme.html",
                    "arguments": [
                        {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 3.0e-3},
                                    {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken","default":120},
                                    {"type": "date_range", "name": "date_range",
                                     "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                                     "default": ""}
                                   ]}

    _HardwareInterfaceClass = SleepDepriverInterfaceCR
    _roi_to_channel = {
            1:1,  3:2,  5:3,  7:4,  9:5,
            12:6, 14:7, 16:8, 18:9, 20:10
        }
    def __init__(self,
                 hardware_connection,
                 velocity_correction_coef=3.0e-3,
                 min_inactive_time=120,  #s
                 date_range=""
                 ):
        """
        A stimulator to control a sleep depriver module.

        :param hardware_connection: the sleep depriver module hardware interface
        :type hardware_connection: :class:`~ethoscope.hardware.interfaces.sleep_depriver_interface.SleepDepriverInterface`
        :param velocity_correction_coef:
        :type velocity_correction_coef: float
        :param min_inactive_time: the minimal time without motion after which an animal should be disturbed (in seconds)
        :type min_inactive_time: float
        :return:
        """

        self._inactivity_time_threshold_ms = min_inactive_time *1000 #so we use ms internally
        self._t0 = None
        
        super(SleepDepStimulator, self).__init__(hardware_connection, velocity_correction_coef, date_range=date_range)




class OptomotorSleepDepriver(SleepDepStimulator):

    _description = {"overview": "A stimulator to sleep deprive an animal using gear motors. See https://github.com/gilestrolab/ethoscope_hardware/tree/master/modules/gear_motor_sleep_depriver",
                "arguments": [
                    {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
                                {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken(s)","default":10},
                                {"type": "number", "min": 500, "max": 10000 , "step": 50, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
                                {"type": "number", "min": 0, "max": 1000, "step": 1, "name": "pulse_intensity",  "description": "intensity of stimulus 0-1000", "default": 1000},
                                {"type": "number", "min": 0, "max": 3, "step": 1, "name": "stimulus_type",  "description": "1 = opto, 2= moto", "default": 2},
                                {"type": "date_range", "name": "date_range",
                                 "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                                 "default": ""}
                               ]}


    _HardwareInterfaceClass = OptoMotor
    _roi_to_channel_opto = {1:1, 3:3, 5:5, 7:7, 9:9,
                            12:23, 14:21,16:19, 18:17, 20:15}
    _roi_to_channel_moto = {1:0, 3:2, 5:4, 7:6, 9:8,
                            12:22, 14:20, 16:18, 18:16, 20:14}
    # default is moto
    _roi_to_channel =      {1:0, 3:2, 5:4, 7:6, 9:8,
                            12:22, 14:20, 16:18, 18:16, 20:14}



    def __init__(self,
                 hardware_connection,
                 velocity_correction_coef=3.0e-3,
                 min_inactive_time=120,  # s
                 pulse_duration = 1000,  #ms
                 pulse_intensity = 1000,
                 stimulus_type = 3,  # 1 = opto, 2= moto, 3 = both
                 date_range=""
                 ):


        self._t0 = None

        # the inactive time depends on the chanel here
        super(OptomotorSleepDepriver, self).__init__(hardware_connection, velocity_correction_coef, min_inactive_time, date_range)


        if stimulus_type == 2:
            self._roi_to_channel = self._roi_to_channel_moto
        elif stimulus_type == 1:
            self._roi_to_channel = self._roi_to_channel_opto

        self._pulse_duration = pulse_duration
        self._pulse_intensity = pulse_intensity

    def _decide(self):
        out, dic = super(OptomotorSleepDepriver, self)._decide()
        dic["duration"] = self._pulse_duration
        dic["intensity"] = self._pulse_intensity
        return out, dic


class GearOptomotorSleepDepriver(OptomotorSleepDepriver):
    """
    Exactly the same as OptomotorSleepDepriver with the difference that the default
    pulse_duration both via CLI and GUI is now 2000 ms and not 1000 ms
    """
    _description = {"overview": "A stimulator to sleep deprive an animal using gear motors. See https://github.com/gilestrolab/ethoscope_hardware/tree/master/modules/gear_motor_sleep_depriver . NOTE: Use this class if you are using a SD module usig the Adafruit TLC5947 chip",
                "arguments": [
                    {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
                                {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken(s)","default":10},
                                {"type": "number", "min": 500, "max": 10000 , "step": 50, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 2000},
                                {"type": "number", "min": 0, "max": 1000, "step": 1, "name": "pulse_intensity",  "description": "intensity of stimulus 0-1000", "default": 1000},
                                {"type": "date_range", "name": "date_range",
                                 "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                                 "default": ""}
                               ]}

    _HardwareInterfaceClass = OptoMotor
    def __init__(self, *args, pulse_duration=2000, **kwargs):
        super(GearOptomotorSleepDepriver, self).__init__(*args, pulse_duration=pulse_duration, **kwargs)
        self._roi_to_channel = {1:0, 3:2, 5:4, 7:6, 9:8,
                                12:22, 14:20, 16:18, 18:16, 20:14}

class RobustSleepDepriver(GearOptomotorSleepDepriver):
    """
    Sleep depriver using new PCB from Giorgio Gilestro.
    """
    _description = {
        "overview": "A stimulator to sleep deprive an animal using gear motors. See https://github.com/gilestrolab/ethoscope_hardware/tree/master/modules/gear_motor_sleep_depriver. NOTE: Use  this class if you are using a SD module using the new PCB (Printed Circuit Board)",
        "arguments": [
            {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 0.01},
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken(s)","default":10},
            {"type": "number", "min": 10, "max": 10000 , "step": 10, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
            {"type": "str", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""}
        ]
    }

    _HardwareInterfaceClass = SleepDepriver

    def __init__(self, *args, **kwargs):
        super(RobustSleepDepriver, self).__init__(*args, **kwargs)
        self._roi_to_channel = {
                1:1,
                3:3,
                5:5,
                7:7,
                9:9,
                12:11,
                14:13,
                16:15,
                18:17,
                20:19
            }


class ExperimentalSleepDepStimulator(SleepDepStimulator):
    _description = {"overview": "A stimulator to sleep deprive an animal using servo motor. See http://todo/fixme.html",
                    "arguments": [
                        {"type": "number", "min": 0.0, "max": 1.0, "step": 0.0001, "name": "velocity_correction_coef", "description": "Velocity correction coef", "default": 3.0e-3},
                                    {"type": "date_range", "name": "date_range",
                                     "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                                     "default": ""}
                                   ]}

    _HardwareInterfaceClass = SleepDepriverInterface
    _roi_to_channel = {
            1:1,  3:2,  5:3,  7:4,  9:5,
            12:6, 14:7, 16:8, 18:9, 20:10
        }

    def __init__(self,
                 hardware_connection,
                 velocity_correction_coef=3.0e-3,
                 date_range=""
                 ):
        """
        A stimulator to control a sleep depriver module.
        This is an experimental version where each channel has a different inactivity_time_threshold.

        :param hardware_connection: the sleep depriver module hardware interface
        :type hardware_connection: :class:`~ethoscope.hardawre.interfaces.sleep_depriver_interface.SleepDepriverInterface`
        :param velocity_correction_coef:
        :type velocity_correction_coef: float
        :return:
        """

        self._t0 = None

        
        # the inactive time depends on the chanel here
        super(ExperimentalSleepDepStimulator, self).__init__(hardware_connection, velocity_correction_coef, 0, date_range)
        self._inactivity_time_threshold_ms = None

    # here we override bind tracker so that we also define inactive time for this stimulator
    def bind_tracker(self, tracker):
        self._tracker = tracker

        roi_id = self._tracker._roi.idx
        try:
            channel = self._roi_to_channel[roi_id]
            self._inactivity_time_threshold_ms = round(channel ** 1.7) * 20 * 1000
        except KeyError:
            pass


class MiddleCrossingStimulator(BaseStimulator):
    _description = {"overview": "A stimulator to disturb animal as they cross the midline",
                    "arguments": [
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":0.01, "name": "p", "description": "the probability to move the tube when a beam cross was detected","default":1.0},
                                    {"type": "number", "min": 0.0, "max": 300.0, "step":1.0, "name": "refractory_period", "description": "the minimum time between stimuli in seconds","default": 5.0},
                                    {"type": "date_range", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""},
                                    {"type": "number", "min": 0, "max": 1, "step": 1, "name": "chip",  "description": "chip for this stimulator. 0: TL5947, 1: Darlington array. Please make sure you chose the right one!", "default": 1}
                                   ]}

    _HardwareInterfaceClass = OptoMotor
    _pulse_duration = 1000 #ms

    def __init__(self,
                 hardware_connection,
                 p=1.0,
                 refractory_period=5.0,
                 chip=1,
                 date_range=""
                 ):
        """
        :param hardware_connection: the sleep depriver module hardware interface
        :type hardware_connection: :class:`~ethoscope.hardawre.interfaces.sleep_depriver_interface.SleepDepriverInterface`
        :param p: the probability of disturbing the animal when a beam cross happens
        :type p: float
        :param refractory_period: the minimum time between stimuli in seconds
        :type p: float
        :return:
        """

        if chip == 1:
            self._roi_to_channel = {1:1, 3:3, 5:5, 7:7, 9:9,
                       12:11, 14:13, 16:15, 18:17, 20:19}
 
        elif chip == 0:
            self._roi_to_channel = {1:0, 3:2, 5:4, 7:6, 9:8,
                       12:22, 14:20, 16:18, 18:16, 20:14}
            


        self._last_stimulus_time = 0
        self._p = p
        self._refractory_period = refractory_period
        
        super(MiddleCrossingStimulator, self).__init__(hardware_connection,  date_range=date_range)

    def _decide(self):
        roi_id = self._tracker._roi.idx
        now = self._tracker.last_time_point
        base_dict = {"duration": self._pulse_duration}
        if now - self._last_stimulus_time < self._refractory_period * 1000:
            return HasInteractedVariable(False), {}

        try:
            channel = self._roi_to_channel[roi_id]
        except KeyError:
            return HasInteractedVariable(False), {}

        positions = self._tracker.positions

        if len(positions) < 2:
            return HasInteractedVariable(False), {}

        if len(positions[-1]) != 1:
            raise Exception("This stimulator can only work with a single animal per ROI")

        roi_w = float(self._tracker._roi.longest_axis)
        x_t_zero = positions[-1][0]["x"] / roi_w - 0.5
        x_t_minus_one = positions[-2][0]["x"] / roi_w - 0.5

        if (x_t_zero > 0) ^ (x_t_minus_one >0): # this is a change of sign

            if random.uniform(0,1) < self._p:
                self._last_stimulus_time = now
                return HasInteractedVariable(True), {"channel": channel, **base_dict}

        return HasInteractedVariable(False), {"channel": channel, **base_dict}





class OptomotorSleepDepriverSystematic(OptomotorSleepDepriver):
    _description = {"overview": "A stimulator to sleep deprive an animal using gear motors. See https://github.com/gilestrolab/ethoscope_hardware/tree/master/modules/gear_motor_sleep_depriver",
                    "arguments": [

                                    {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "interval", "description": "The recurence of the stimulus","default":120},
                                    {"type": "number", "min": 500, "max": 10000 , "step": 50, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
                                    {"type": "number", "min": 0, "max": 3, "step": 1, "name": "stimulus_type",  "description": "1 = opto, 2= moto", "default": 2},
                                    {"type": "date_range", "name": "date_range",
                                     "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)",
                                     "default": ""}
                                   ]}

    _HardwareInterfaceClass = OptoMotor
    _roi_to_channel_opto = {1:1, 3:3, 5:5, 7:7, 9:9,
                            12:23, 14:21,16:19, 18:17, 20:15}
    _roi_to_channel_moto = {1:0, 3:2, 5:4, 7:6, 9:8,
                            12:22, 14:20, 16:18, 18:16, 20:14}


    def __init__(self,
                 hardware_connection,
                 interval=120,  # s
                 pulse_duration = 1000,  #ms
                 stimulus_type = 2,  # 1 = opto, 2= moto, 3 = both
                 date_range=""
                 ):



        self._interval = interval  *1000 # ms used internally

        super(OptomotorSleepDepriverSystematic, self).__init__(hardware_connection, 0,0,
                                                               pulse_duration, stimulus_type,
                                                               date_range)

        self._t0 = 0

    def _decide(self):
        roi_id = self._tracker._roi.idx
        try:
            channel = self._roi_to_channel[roi_id]
        except KeyError:
            return HasInteractedVariable(False), {}
        now = self._tracker.last_time_point + roi_id *100
        if now - self._t0 > 1000 and (now % self._interval) < 100:
            dic = {"channel": channel}
            dic["duration"] = self._pulse_duration
            self._t0 = now
            return HasInteractedVariable(True), dic

        return HasInteractedVariable(False), {}

class RobustOptomotorSleepDepriverSystematic(OptomotorSleepDepriverSystematic):

    _description = {
        "overview": "A stimulator to sleep deprive an animal using gear motors. See https://github.com/gilestrolab/ethoscope_hardware/tree/master/modules/gear_motor_sleep_depriver",
        "arguments": [
            {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "interval", "description": "The recurence of the stimulus","default":120},
            {"type": "number", "min": 500, "max": 10000 , "step": 50, "name": "pulse_duration", "description": "For how long to deliver the stimulus(ms)", "default": 1000},
            {"type": "date_range", "name": "date_range", "description": "A date and time range in which the device will perform (see http://tinyurl.com/jv7k826)", "default": ""}
        ]
    }

    _HardwareInterfaceClass = OptoMotor
    _roi_to_channel_opto = {1:1, 3:3, 5:5, 7:7, 9:9,
                            12:23, 14:21,16:19, 18:17, 20:15}
    _roi_to_channel_moto = {1:0, 3:2, 5:4, 7:6, 9:8,
                            12:22, 14:20, 16:18, 18:16, 20:14}


    def __init__(self,
                 hardware_connection,
                 pulse_duration = 1000,  #ms
                 date_range="", **kwargs
                 ):


        super(RobustOptomotorSleepDepriverSystematic, self).__init__(
            hardware_connection,
            pulse_duration=pulse_duration,
            stimulus_type=None,
            date_range=date_range, **kwargs
        )

        self._roi_to_channel = {1:1, 3:3, 5:5, 7:7, 9:9, 12:11, 14:13, 16:15, 18:17, 20:19}


if __name__ == "__main__":

    import numpy as np
    from ethoscope.trackers.adaptive_bg_tracker import AdaptiveBGModel
    from ethoscope.core.roi import ROI 
    from ethoscope.hardware.interfaces.interfaces import HardwareConnection

    def never_moving():
        return False

    hc = HardwareConnection(RobustSleepDepriver._HardwareInterfaceClass, do_warm_up=False)

    sd = RobustSleepDepriver(
            hc,
            velocity_correction_coef=0.01,
            min_inactive_time=10,  # s
            pulse_duration = 1000,  #ms
            date_range=""
    )
    sd._has_moved = never_moving
    sd._t0 = 0

    roi = ROI(polygon=np.array([[0, 10], [10, 10], [10, 0], [0, 0]]), idx=1)
    tracker = AdaptiveBGModel(roi=roi)
    tracker._last_time_point = 30000 #ms

    sd.bind_tracker(tracker)
    print("Applying")
    interact, result = sd.apply()
    print(interact)
    print(result)
    while len(hc._instructions) != 0:
        time.sleep(1)
    hc.stop()
