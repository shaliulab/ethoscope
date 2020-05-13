import urllib.request
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--ip")
ap.add_argument("--port", default=9000)

ARGS = vars(ap.parse_args())

STATIC_DIR = "static"
INDEX_FILE = "ethoscope_data/results/index.html"
url = "/".join(["http://%s:%i"%(ARGS["ip"], ARGS["port"]), STATIC_DIR, INDEX_FILE])
response = urllib.request.urlopen(url)
out = [r.decode('utf-8').rstrip() for r in response]
dates = [e.split("/")[5] for e in out]
last_date = sorted(list(set(dates)))[::-1][0]
print(last_date)
res = sum([e == last_date for e in dates])
print(res)

