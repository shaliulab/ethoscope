import re

def filter_by_regex(devices, regex):
    pattern = re.compile(regex)
    devices = [e for e in devices if pattern.match(e["ethoscope_name"]) is not None]
    return devices
