import logging

from ethoscope.hardware.interfaces.optomotor import OptoMotor

class CleanUpHardware(OptoMotor):

    def cleanup(self):
        for channel in range(self._n_channels):
            logging.warning(f"Turning off channel {channel}")
            self.send(channel, turnon=False)

class StaticOptogeneticHardware(CleanUpHardware):
    _inst_format = {True: "S {channel}\r\n", False: "U {channel}\r\n"}
    _params = ["channel"]

    def __init__(self, *args, **kwargs):
        kwargs["do_warm_up"] = False
        super(StaticOptogeneticHardware, self).__init__(*args, **kwargs)

    def send(self, channel, turnon):
        self.activate(channel, turnon)

    def make_instruction(self, channel, turnon):
        instruction = self._inst_format[turnon].format_map({"channel": channel}).encode("utf-8")
        return instruction

class IndefiniteOptogeneticHardware(CleanUpHardware):
    _inst_format = {True: "W {channel} {pulse_on} {pulse_off}\r\n", False: "U {channel}\r\n"}
    _params = ["channel", "pulse_on", "pulse_off"]

    def __init__(self, *args, **kwargs):
        kwargs["do_warm_up"] = False
        super(IndefiniteOptogeneticHardware, self).__init__(*args, **kwargs)

    def send(self, channel, turnon, *args, **kwargs):
        self.activate(channel, turnon, *args, **kwargs)

    def make_instruction(self, channel, turnon, pulse_on=None, pulse_off=None):

        if turnon:
            assert pulse_on is not None
            assert pulse_off is not None
            params = {"channel": channel, "pulse_on": pulse_on, "pulse_off": pulse_off}
        else:
            params = {"channel": channel}

        instruction = self._inst_format[turnon].format_map(params).encode("utf-8")
        return instruction

class OptogeneticHardware(CleanUpHardware):
    _params = ["channel", "duration", "intensity", "pulse_on", "pulse_off"]

    def __init__(self, *args, **kwargs):
        kwargs["do_warm_up"] = False
        super(OptogeneticHardware, self).__init__(*args, **kwargs)

    def send(self, channel, duration=10000, intensity=1000, pulse_on=50, pulse_off=50):
        self.activate(channel, duration, intensity, pulse_on, pulse_off)

    def val_params(self, channel=None, duration=None, intensity=None, pulse_on=None, pulse_off=None):
        params = super().val_params(channel, duration, intensity)
        params.update({
            "pulse_on": pulse_on,
            "pulse_off": pulse_off,
        })
        return params

    def make_instruction(self, *args, **kwargs):
        params = self.val_params(*args, **kwargs)

        if params["pulse_on"] is None and params["pulse_off"] is None:
            inst_format = "P {channel} {duration}\r\n"
        else:
            inst_format = "R {channel} {duration} {pulse_on} {pulse_off}\r\n"
        try:
            instruction = inst_format.format_map(params).encode("utf-8")
        except TypeError as error:
            logging.error(f"You have passed the wrong amount of things to complete the instruction. You need {len(self._params)} but you passed {len(params)}")
            raise error
        return instruction

        return params
