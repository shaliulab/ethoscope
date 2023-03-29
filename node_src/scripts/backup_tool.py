from ethoscope_node.utils.configuration import EthoscopeConfiguration
from ethoscope_node.utils.backups_helpers import GenericBackupWrapper, BackupClass, receive_devices

import logging
import optparse
import traceback
import os

server = "localhost"
info_file = "/var/run/ethoscope_backup"


def backup_job(args):
    try:
        logging.warning(args)
        device_info, results_dir, use_last_file = args
        logging.info("Initiating backup for device  %s" % device_info["id"])

        with open(info_file, "w") as f:
            f.write(device_info["id"])

        # uncomment this if you plugged a particular ethoscope to the router via cable
        # # and you want to back it up via cable
        # if device_info["name"] == "ETHOSCOPE_016":
        #     # figure out the ip of the ethoscope
        #     # by running on the terminal in an ssh session in the ethoscope:
        #     # ifconfig eth0 | grep "inet "
        #     device_info["ip"] = "192.169.123.121"
        #     print(device_info)

        backup_job = BackupClass(device_info, results_dir=results_dir, use_last_file=use_last_file)
        logging.info("Running backup for device  %s" % device_info["id"])
        backup_job.run()
        logging.info("Backup done for for device  %s" % device_info["id"])
        return 1

    except Exception as e:
        logging.error("Unexpected error in backup. args are: %s" % str(args))
        logging.error(traceback.format_exc())
        return



if __name__ == '__main__':

    CFG = EthoscopeConfiguration()

    logging.getLogger().setLevel(logging.INFO)
    try:
        parser = optparse.OptionParser()
        parser = optparse.OptionParser()
        parser.add_option("-D", "--debug", dest="debug", default=False, help="Set DEBUG mode ON", action="store_true")
        parser.add_option("-r", "--results-dir", dest="results_dir", help="Where result files are stored")
        parser.add_option("-i", "--server", dest="server", default="localhost", help="The server on which the node is running will be interrogated first for the device list")
        parser.add_option("-s", "--safe", dest="safe", default=False, help="Set Safe mode ON", action="store_true")
        parser.add_option("-u", "--use-last-file", dest="use", default=False, help="Set last file if backup path cannot be found", action="store_true")
        parser.add_option("-e", "--ethoscope", dest="ethoscope", help="Force backup of given ethoscope number (eg: 007)")
        parser.add_option("--regex", dest="regex", help="Only backup ethoscopes whose ethoscope_name matches this regex. All are matched by default. Example ^ETHOSCOPE_\d{3}$", default=None)

        (options, args) = parser.parse_args()
        option_dict = vars(options)
        RESULTS_DIR = option_dict["results_dir"] or CFG.content['folders']['results']['path']
        SAFE_MODE = option_dict["safe"]
        USE_LAST_FILE = option_dict["use"]
        ethoscope = option_dict["ethoscope"]
        server = option_dict["server"]
        regex = option_dict["regex"]

        logging.warning("####################################################")
        logging.warning(f"PLEASE NOTE: ETHOSCOPE_DIR is set to {RESULTS_DIR}")
        logging.warning("####################################################")

        if ethoscope:
            all_devices = receive_devices(server)
            bj = None


            for devID in all_devices:
                try:
                    ethoscope = int(ethoscope)
                    condition = all_devices[devID]['name'] == ("ETHOSCOPE_%03d" % ethoscope) and all_devices[devID]['status'] != "offline"
                except ValueError as e:
                    condition = all_devices[devID]['name'] == (f"ETHOSCOPE_{ethoscope}") and all_devices[devID]['status'] != "offline"

                if condition:
                    print(f"Forcing backup for ethoscope ETHOSCOPE_{ethoscope}")
                    bj = backup_job((all_devices[devID], RESULTS_DIR, USE_LAST_FILE))
            if bj == None: exit(f"ETHOSCOPE_{ethoscope} is not online or not detected")

        else:

            gbw = GenericBackupWrapper(backup_job,
                                       RESULTS_DIR,
                                       SAFE_MODE,
                                       server,
                                       regex,
                                       USE_LAST_FILE)
            gbw.run()

    except Exception as e:
        logging.error(traceback.format_exc())
