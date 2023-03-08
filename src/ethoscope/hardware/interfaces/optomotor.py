import logging
import time
import serial
from ethoscope.hardware.interfaces.interfaces import BaseInterface


class WrongSerialPortError(Exception):
    pass


class NoValidPortError(Exception):
    pass


class OptoMotor(BaseInterface):
    _baud = 115200
    _n_channels = 24
    _inst_format = "P {channel} {duration} {intensity}\r\n"
    _params = ["channel", "duration", "intensity"]

    def __init__(self, port=None, *args, **kwargs):
        """
        TODO

        :param port: the serial port to use. Automatic detection if ``None``.
        :type port: str.
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """
        # lazy import
        import serial
        logging.info("Connecting to GMSD serial port...")

        self._serial = None
        if port is None:
            self._port = self._find_port()
        else:
            self._port = port

        self._serial = serial.Serial(self._port, self._baud, timeout=2)
        time.sleep(2)
        self._test_serial_connection()
        super(OptoMotor, self).__init__(*args, **kwargs)

    def _find_port(self):
        from serial.tools import list_ports
        import serial
        import os
        all_port_tuples = list_ports.comports()
        logging.info("listing serial ports")
        all_ports = set()
        for ap, _, _ in all_port_tuples:
            p = os.path.basename(ap)
            print(p)
            if p.startswith("ttyUSB") or p.startswith("ttyACM"):
                all_ports |= {ap}
                logging.info("\t%s", str(ap))

        if len(all_ports) == 0:
            logging.error("No valid port detected!. Possibly, device not plugged/detected.")
            raise NoValidPortError()

        elif len(all_ports) > 2:
            logging.info("Several port detected, using first one: %s", str(all_ports))
        return all_ports.pop()

    def __del__(self):
        if self._serial is not None:
            self._serial.close()
            #

    def _test_serial_connection(self):
        return

    def val_params(self, channel, duration=None, intensity=None):
        """
        Make sure the parameters that will be used to make the instruction
        make sense and have the right type
        """

        if channel < 0:
            raise Exception("chanel must be greater or equal to zero")

        duration = int(duration)
        if intensity is not None:
            intensity = int(intensity)

        params = {"channel": channel, "duration": duration, "intensity": intensity}
        return params


    # I need to pass them None so they are populated from kwargs
    # but they actually should never be None
    def make_instruction(self, *args, **kwargs):
        """
        Produce an instruction that can be passed to the serial handler write method (i.e. to Arduino) 
        :param channel: the chanel idx to be activated
        :type channel: int
        :param duration: the time (ms) the stimulus should last for
        :type duration: int
        :param intensity: duty cycle, between 0 and 1000.
        :type intensity: int
        :return:
        """

        params = self.val_params(*args, **kwargs)
        try:
            instruction = self._inst_format.format_map(params).encode("utf-8")
        except TypeError as error:
            logging.error(f"You have passed the wrong amount of things to complete the instruction. You need {len(self._params)} but you passed {len(params)}")
            raise error
        return instruction


    def activate(self, *args, **kwargs):
        """
        Activates a component on a given channel of the PWM controller
        Parameters are given by make_instruction
        """

        instruction = self.make_instruction(*args, **kwargs)
        logging.warning(instruction)
        o = self._serial.write(instruction)
        return o

    def send(self, channel, duration=10000, intensity=1000):
        self.activate(channel, duration, intensity)

    def _warm_up(self):
        for i in range(self._n_channels):
            self.send(i, duration=1000)
            time.sleep(1.000) #s


class SleepDepriver(OptoMotor):
    """
    An optomotor without intensity regulation
    """
    _inst_format = "P {channel} {duration}\r\n"
    # _n_channels defines the for loop that is
    # iterated when doing the warm up
    # It assumes that the chip set pins
    # cover the [0,   _n_channels - 1] interval (both included)
    # It's possible Arduino maps everything >= _n_channels
    # to the first channel
    # i.e. a warm up of the channels 20-24 activates 5 times
    # the first channel, something undesirable
    _n_channels = 20


if __name__ == "__main__":
    found = False
    port = 0
    while not found:
        try:
            sd = SleepDepriver(port=f"/dev/ttyACM{port}", do_warm_up=False)
            found = True
        except serial.SerialException:
            port += 1

    sd.activate(1, 100, 1000)
    time.sleep(1)
    sd.activate(1, 200, 1000)
    time.sleep(1)
    sd.activate(1, 500, 1000)
    time.sleep(1)
    sd.activate(1, 1000, 1000)

