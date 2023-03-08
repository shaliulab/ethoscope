from ethoscope.hardware.interfaces.optomotor import OptoMotor


class StaticOptogeneticHardware(OptoMotor):
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
    
class IndefiniteOptogeneticHardware(OptoMotor):
    _inst_format = {True: "S {channel} {pulse_on} {pulse_off}\r\n", False: "U {channel}\r\n"}
    _params = ["channel", "pulse_on", "pulse_off"]

    def __init__(self, *args, **kwargs):
        kwargs["do_warm_up"] = False
        super(IndefiniteOptogeneticHardware, self).__init__(*args, **kwargs)

    def send(self, channel, pulse_on, pulse_off, turnon):
        self.activate(channel, pulse_on, pulse_off, turnon)

    def make_instruction(self, channel, pulse_on, pulse_off, turnon):

        if turnon:
            params = {"channel": channel, "pulse_on": pulse_on, "pulse_off": pulse_off}
        else:
            params = {"channel": channel}

        instruction = self._inst_format[turnon].format_map(params).encode("utf-8")
        return instruction

class OptogeneticHardware(OptoMotor):
    _inst_format = "R {channel} {duration} {pulse_on} {pulse_off}\r\n"
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
