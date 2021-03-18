import logging
import time
from ethoscope.hardware.interfaces.interfaces import BaseInterface


class WrongSerialPortError(Exception):
    pass


class NoValidPortError(Exception):
    pass


class OptoMotor(BaseInterface):
    _baud = 115200
    _n_channels = 24
    _inst_format = b"P %i %i %i\r\n"
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

    def val_params(self, channel, duration, intensity=None):
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

    def filter_params(self, params):
        """
        Only pass the params listed in self._params
        """

        params_final = dict(params)
        for param in params:
            if param not in self._params:
                params_final.pop(param)

        return params_final

    def make_instruction(self, channel, duration, intensity):
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
 
        params = self.val_params(channel, duration, intensity)
        params = self.filter_params(params)
        try:
            instruction = self._inst_format % params
        except TypeError as error:
            logging.error(f"You have passed the wrong amount of things to complete the instruction. You need {self._inst_param_count} but you passed {len(params)}")
            raise error
        return instruction


    def activate(self, **kwargs):
        """
        Activates a component on a given channel of the PWM controller
        Parameters are given by make_instruction

       """
        instruction = self.make_instruction(**kwargs)
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
    _inst_format = b"P %i %i\r\n"
    _params = ["channel", "duration"]
