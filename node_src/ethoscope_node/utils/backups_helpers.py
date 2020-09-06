from ethoscope_node.utils.device_scanner import EthoscopeScanner
from ethoscope_node.utils.mysql_backup import MySQLdbToSQlite, DBNotReadyError

import os
import logging
import time
import multiprocessing
import traceback

import urllib.request
import json

import re

cpu_available = multiprocessing.cpu_count()
#n_parallel_threads = cpu_available
n_parallel_threads = 4

def filter_by_regex(devices, regex):
    pattern = re.compile(regex)
    #ipdb.set_trace()
    if type(devices) is dict:
        new_devices = {}
        for key, value in devices.items():
            if pattern.match(value["name"]) is not None:
                new_devices[key] = value

        devices = new_devices
        return devices

    else:
        devices = [e for e in devices if pattern.match(e["ethoscope_name"]) is not None]
        return devices

def receive_devices(server = "localhost", regex=None):
    '''
    Interrogates the NODE on its current knowledge of devices, then extracts from the JSON record
    only the IPs
    '''
    url = "http://%s/devices" % server
    devices = []

    try:
        req = urllib.request.Request(url, headers={'Content-Type': 'application/json'})
        f = urllib.request.urlopen(req, timeout=10)
        devices = json.load(f)
        return devices

    except:
        logging.error("The node ethoscope server %s is not running or cannot be reached. A list of available ethoscopes could not be found." % server)
        return
        #logging.error(traceback.format_exc())


class BackupClass(object):
    _db_credentials = {
            "name":"ethoscope_db",
            "user":"ethoscope",
            "password":"ethoscope"
        }

    # #the db name is specific to the ethoscope being interrogated
    # #the user remotely accessing it is node/node

    # _db_credentials = {
            # "name":"ETHOSCOPE_000_db",
            # "user":"node",
            # "password":"node"
        # }

    def __init__(self, device_info, results_dir):

        self._device_info = device_info
        self._database_ip = os.path.basename(self._device_info["ip"])
        self._results_dir = results_dir


    def run(self):
        try:
            if "backup_path" not in self._device_info:
                raise KeyError("Could not obtain device backup path for %s" % self._device_info["id"])

            if self._device_info["backup_path"] is None:
                raise ValueError("backup path is None for device %s" % self._device_info["id"])
            backup_path = os.path.join(self._results_dir, self._device_info["backup_path"])

            self._db_credentials["name"] = "%s_db" % self._device_info["name"]

            mirror= MySQLdbToSQlite(backup_path, self._db_credentials["name"],
                            remote_host=self._database_ip,
                            remote_pass=self._db_credentials["password"],
                            remote_user=self._db_credentials["user"])

            mirror.update_roi_tables()

        except DBNotReadyError as e:
            logging.warning(e)
            logging.warning("Database %s on IP %s not ready, will try later" % (self._db_credentials["name"], self._database_ip) )
            pass

        except Exception as e:
            logging.error(traceback.format_exc())


def dummy_job(*args):
    logging.warning("Hello World")


class GenericBackupWrapper(object):
    def __init__(self, backup_job, results_dir, safe, server, regex=None):
        self._TICK = 1.0  # s
        self._BACKUP_DT = 5 * 60  # 5min
        # self._BACKUP_DT = 5
        self._results_dir = results_dir
        self._safe = safe
        self._backup_job = backup_job
        self._server = server
        self._regex = regex

        # for safety, starts device scanner too in case the node will go down at later stage
        self._device_scanner = EthoscopeScanner(results_dir = results_dir, regex = regex)




    def run(self):
        try:
            devices = receive_devices(self._server)
            if self._regex is not None:
                devices = filter_by_regex(devices, self._regex)


            if not devices:
                logging.info("Using Ethoscope Scanner to look for devices")
                self._device_scanner.start()
                time.sleep(20)

            t0 = time.time()
            t1 = t0 + self._BACKUP_DT

            while True:

                if t1 - t0 < self._BACKUP_DT:
                    t1 = time.time()
                    time.sleep(self._TICK)
                    continue

                with open("/etc/backup_off.conf", "r") as fh:
                    backup_off  = [e.strip("\n") for e in fh.readlines()]

                logging.info("Starting backup")
                logging.info("Following ethoscopes will NOT be backed up")
                logging.info(backup_off)
                logging.info("%s ethoscopes will be backed up simultaneously", n_parallel_threads)

                if not devices:
                    devices = self._device_scanner.get_all_devices_info()
                    if self._regex is not None:
                        devices = filter_by_regex(devices, self._regex)

                dev_list = str([d for d in sorted(devices.keys())])
                logging.info("device map is: %s" %dev_list)

                args = []
                for d in list(devices.values()):
                    if d["status"] not in ["not_in_use", "offline"] and d["name"] not in backup_off:
                        args.append((d, self._results_dir))

                logging.info("Found %s devices online" % len(args))

                logging.warning(args)
                if self._safe:
                    for arg in args:
                        self._backup_job(arg)
                        #dummy_job(arg)

                    #map(self._backup_job, args)
                else:
                    pool = multiprocessing.Pool(int(n_parallel_threads))
                    _ = pool.map(self._backup_job, args)
                    #_ = pool.map(dummy_job, args)
                    logging.info("Pool mapped")
                    pool.close()
                    logging.info("Joining now")
                    pool.join()
                t1 = time.time()
                logging.info("Backup finished at t=%i" % t1)
                t0 = t1
                # actually dont loop forever and instead do it once
                # we have moved the loop-like behavior with a crontab service
                # that runs the backup_tool.py script every 5 minutes
                break

        finally:
            if not devices:
                self._device_scanner.stop()
