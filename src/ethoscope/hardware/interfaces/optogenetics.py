from ethoscope.hardware.interfaces.optomotor import OptoMotor

class OptogeneticHardware(OptoMotor):
    _inst_format = "R {channel} {duration} {pulse_on} {pulse_off}\r\n"
    _params = ["channel", "duration", "intensity", "pulse_on", "pulse_off"]


    def send(self, channel, duration=10000, intensity=1000, pulse_on=50, pulse_off=50):
        self.activate(channel, duration, intensity, pulse_on, pulse_off)

    def val_params(self, channel=None, duration=None, intensity=None, pulse_on=None, pulse_off=None):
        params = super().val_params(channel, duration, intensity)
        params.update({
            "pulse_on": pulse_on,
            "pulse_off": pulse_off,
        })

        return params