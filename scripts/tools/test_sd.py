import argparse
import logging
import subprocess 
import os
import warnings
from sd_server import SDServer


class SDClient:

    def __init__(self, port):
        self._port = port
        self._roi_to_channel = {1:1, 3:3, 5:5, 7:7, 9:9, 12:11, 14:13, 16:15, 18:17, 20:19}

    def get_channels(self, region_ids):
        channels = []
        for roi in region_ids:
            if roi in self._roi_to_channel:
                channels.append(str(self._roi_to_channel[roi]))

        channels_str = ", ".join(channels)
        channels_str = "[" + channels_str + "]"
        return channels_str

    def activate(self, region_ids, duration=1000):

        binary = "/usr/bin/curl"
        method = "-X POST"
        header = "-H \"Content-Type: application/json\""
        
        channels = self.get_channels(region_ids)
        dictionary = "-d '{\"channels\": %s, \"duration\": %d}'" % (channels, duration)

        dest = f"localhost:{self._port}/activate"

        cmd = f"{binary} {method} {header} {dictionary} {dest}"
        os.system(cmd)


    @staticmethod
    def format_region_ids(region_ids):
        region_ids = region_ids.split(" ")
        region_ids_int = []
        for r in region_ids:
            if r == "":
                pass
            else:
                region_ids_int.append(int(r))

        return region_ids_int


    def run(self):

        while True:

            try:
                region_ids = input("Please enter region ids. Example: 1 3 5 20.\n")
                if region_ids == "":
                    warnings.warn("Please enter a valid region_id")
                    continue

                region_ids = self.format_region_ids(region_ids)
                
                duration  = input("Please enter stimulus duration in ms [1000]\n")
                if duration == "":
                    duration = 1000

                self.activate(region_ids, duration)

            except KeyboardInterrupt:
                break

        return 0

    def start(self):
        return self.run()



if __name__ == "__main__":

    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9001)
    args = ap.parse_args()


    sd_server = SDServer(port=args.port, debug=True)
    sd_server.setDaemon(True)
    sd_server.start()

    sd_client = SDClient(port=args.port)
    sd_client.start()

#cmd = "/usr/bin/curl -X POST -H \"Content-Type: application/json\" -d '{\"channels\": %s, \"duration\": %d}' localhost:%d/activate" % (channels_str, args.duration, args.port)
