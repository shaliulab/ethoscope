import re
import datetime
import time
import logging
import warnings

logger = logging.getLogger(__name__)

class DateRangeError(Exception):
    pass

class Scheduler(object):
    def __init__(self, in_str):
        """
        Class to express time constrains.
        It parses a formated string to define a list of allowed time range.
        Then it can be used to assess if a date and time is within a valid range.
        This is useful to control stimulators and other utilities.

        :param in_str: A formatted string. Format described `here <https://github.com/gilestrolab/ethoscope/blob/master/user_manual/schedulers.md>`_
        :type in_str: str
        """
        date_range_str = in_str.split(",")
        self._date_ranges = []
        for drs in  date_range_str:
            dr = self._parse_date_range(drs)

            self._date_ranges.append(dr)
        self._check_date_ranges(self._date_ranges)

    def _check_date_ranges(self, ranges):
        all_dates = []
        for start,end in ranges:
            all_dates.append(start)
            all_dates.append(end)

        for i  in  range(0, len(all_dates)-1):
            if (all_dates[i+1] - all_dates[i]) <= 0:
                raise DateRangeError("Some date ranges overlap")
        pass

    def check_time_range(self, t = None):
        """
        Check whether a unix timestamp is within the allowed range.
        :param t: the time to test. When ``None``, the system time is used
        :type t: float
        :return: ``True`` if the time was in range, ``False`` otherwise
        :rtype: bool
        """
        if t is None:
            t= time.time()
        return self._in_range(t)

    def _in_range(self, t):
        for r in self._date_ranges:
            if r[1] > t > r[0]:
                return True
        return False

    def _parse_date_range(self, str):
        self._start_date = 0
        self._stop_date = float('inf')
        dates = re.split("\s*>\s*", str)

        if len(dates) > 2:
            raise DateRangeError(" found several '>' symbol. Only one is allowed")
        date_strs = []
        for d in dates:
            date_strs.append(self._parse_date(d))

        if len(date_strs) == 1:
            # start_date
            if date_strs[0] is None:
                out =  (0,float("inf"))
            else:
                out = (date_strs[0], float("inf"))

        elif len(date_strs) == 2:
            d1, d2 = date_strs
            if d1 is None:
                if d2 is None:
                    raise DateRangeError("Data range cannot inclue two None dates")
                out =  (0, d2)
            elif d2 is None:
                out =  (d1, float("inf"))
            else:
                out =  (d1, d2)
        else:
            raise Exception("Unexpected date string")
        if out[0] >= out[1]:
            raise DateRangeError("Error in date %s, the end date appears to be in the past" % str)
        return out


    @staticmethod
    def totimestamp(datestr):
        return time.mktime(datetime.datetime.strptime(datestr,'%Y-%m-%d %H:%M:%S').timetuple())
        
    def _parse_date(self, str):
        pattern = re.compile("^\s*(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})\s*$")
        if re.match("^\s*$", str):
            return None
        if not re.match(pattern, str):
            raise DateRangeError("%s not match the expected pattern" % str)
        datestr = re.match(pattern, str).groupdict()["date"]
        return self.totimestamp(datestr)


class SegmentedScheduler(Scheduler):

    """
    Advanced sleep deprivation

    Use this scheduler to program a different stimulus duration
    for different segments of the sleep deprivation treatment

    Format the input string as follows

    RANGE_START > RANGE_END;HOUR_SINCE ~ DURATION|HOUR_SINCE ~ DURATION
    """

    def __init__(self, *args, program="", **kwargs):


        super().__init__(*args, **kwargs)
        self._programs = program.split(",")
        self._validate_programs()

    def _validate_programs(self):
        for pr in self._programs:
            try:
                self.parse_program(pr)
            except Exception as error:
                logger.warning(f"Could not parse program {pr}")
                raise error

        return 0

    def check_duration(self, t=None):
        """
        Return the interaction duration that should be delivered
        or None if the default should be used or at least
        or no alternative is clear:

        An alternative is not clear if:
        this function finds it is out of range (possible due to overhead).
        Maybe we were when called but not when running)
        """


        if t is None:
            t = time.time()

        index = None
        for i, r in enumerate(self._date_ranges):
            if r[1] > t > r[0]:
                index = i
                hours_since_range_start = (t - r[0]) / 3600
                hours_to_finish = (r[1] - t) / 3600
                break

        if hours_to_finish < 0 or hours_since_range_start < 0:
            warnings.warn("I am not in a range but I somehow got called")
            warnings.warn("I will return a default duration:")
            return None

        # this is possible if
        # we are not in any range

        # also possible if we just finished a range
        # in the time between the first check in stimulator.apply()
        # and here
        if index is None:
            return None
        
        program = self._programs[index]
        times, durations = self.parse_program(program)

        for t_i in range(0, len(times)):
            
            if t_i == (len(times) - 1):
                return durations[-1]
            elif hours_since_range_start > times[t_i] and hours_since_range_start < times[t_i+1]:
                return durations[t_i]

        return None


    @staticmethod
    def parse_program(program):
        """
        Given a program, return the duration that should be delivered now
        """

        time_to_duration_separator = ">"
        steps_separator = ";"

        steps = program.split(steps_separator)
        times = []
        durations = []
        old_hours_since = 0
        for step in steps:
            hours_since, duration = step.split(time_to_duration_separator)
            hours_since = int(hours_since.replace(" ", ""))
            if hours_since <= old_hours_since and old_hours_since != 0:
                raise Exception(
                        """
                        Scheduler string format is wrong.
                        Please make sure all timepoints
                        are passed in chronologically increasing order
                        There should be no duplicates either 
                        """
                        )
            times.append(hours_since)
            duration = int(duration.replace(" ", ""))
            durations.append(duration)
            old_hours_since = hours_since

        return times, durations



if __name__ == "__main__":

    schedule = SegmentedScheduler(in_str="2021-05-05 22:00:00 > 2021-05-06 10:00:00", program="0 > 250;3 > 500;6 > 750;9 > 1000")
    d250 = schedule.check_duration(schedule.totimestamp("2021-05-05 23:00:00"))
    d500 = schedule.check_duration(schedule.totimestamp("2021-05-06 02:00:00"))
    d750 = schedule.check_duration(schedule.totimestamp("2021-05-06 05:00:00"))
    print(d250, d500, d750)

    






