import re

def filter_by_regex(all_known_ethoscopes, regex):
    pattern = re.compile(regex)
    all_known_ethoscopes = [e for e in all_known_ethoscopes if pattern.match(e["ethoscope_name"]) is not None]
    return all_known_ethoscopes
