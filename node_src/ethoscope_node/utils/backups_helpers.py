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
from os import stat
from pwd import getpwuid, getpwnam

cpu_available = multiprocessing.cpu_count()
#n_parallel_threads = cpu_available
n_parallel_threads = 8

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

    def infer_backup_path(self):
        import datetime
        import subprocess
        machine_id = self._device_info["id"]
        machine_name = self._device_info["name"]
        sql_cmd = f"USE {machine_name}_db; SELECT value FROM METADATA WHERE field='date_time';"
        ip_address = self._device_info["ip"]
        cmd = f'mysql -uethoscope -pethoscope -h {ip_address} -e'.split(" ") + [sql_cmd]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        data = p.communicate()
        date_time_float = float(data[0].decode().split("\n")[1])
        datetime_str = datetime.datetime.fromtimestamp(date_time_float).strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = os.path.join(self._results_dir, machine_id, machine_name, datetime_str, datetime_str + "_" + machine_id + ".db")
        return backup_path


    def __init__(self, device_info, results_dir, use_last_file=False):

        self._device_info = device_info
        self._database_ip = os.path.basename(self._device_info["ip"])
        self._results_dir = results_dir
        self._use_last_file = use_last_file

    def _get_backup_path(self):
        if "backup_path" not in self._device_info:
            logging.warning("Could not obtain device backup path for %s. I will infer it" % self._device_info["id"])
            backup_path = self.infer_backup_path()

        elif self._device_info["backup_path"] is None:
            raise ValueError("backup path is None for device %s" % self._device_info["id"])

        else:
            backup_path = os.path.join(self._results_dir, self._device_info["backup_path"])
        
        return backup_path

    def run(self):
        try:

            backup_path = self._get_backup_path()

            self._db_credentials["name"] = "%s_db" % self._device_info["name"]

            mirror= MySQLdbToSQlite(backup_path, self._db_credentials["name"],
                            remote_host=self._database_ip,
                            remote_pass=self._db_credentials["password"],
                            remote_user=self._db_credentials["user"])

            mirror.update_roi_tables()


        except KeyError as e:
            if self._use_last_file:

                logging.warning('Using last file')
                ethoscope_dir = os.path.join(self._results_dir, self._device_info["id"], self._device_info["name"])
                datetime_folder = sorted(os.listdir(ethoscope_dir))[-1]
                logging.warning(datetime_folder)
                experiment_folder = os.path.join(ethoscope_dir, datetime_folder)
                files = os.listdir(experiment_folder)
                dbfile = [f for f in files if f[::-1][:3] == "bd."][0]
                backup_path = os.path.join(experiment_folder, dbfile)

                answer = 'INVALID'
                while answer != 'N' and answer != 'Y':
                    answer = input(f'I will assume the correct backup path is {backup_path}. Is this correct? Y/N')
                    if answer == 'Y':

                        self._db_credentials["name"] = "%s_db" % self._device_info["name"]

                        mirror= MySQLdbToSQlite(backup_path, self._db_credentials["name"],
                                        remote_host=self._database_ip,
                                        remote_pass=self._db_credentials["password"],
                                        remote_user=self._db_credentials["user"])

                        mirror.update_roi_tables()
                    elif answer == 'N':
                        raise e
                    else:
                        print('Please enter a valid answer. Either Y or N')

            else:
                raise e

        except DBNotReadyError as e:
            logging.warning(e)
            logging.warning("Database %s on IP %s not ready, will try later" % (self._db_credentials["name"], self._database_ip) )
            pass

        except Exception as e:
            logging.error(traceback.format_exc())


        self.finish_backup()


    @staticmethod
    def find_owner(filename):
        return getpwuid(stat(filename).st_uid).pw_name

    @staticmethod
    def change_owner(filename, new_owner="vibflysleep"):
        uid = getpwnam(new_owner).pw_uid
        gid = getpwnam(new_owner).pw_gid
        os.chown(filename, uid, gid)

    def finish_backup(self):
        backup_path = self._get_backup_path()
        if os.path.exists(backup_path):
            owner = self.find_owner(backup_path)
            if owner != "vibflysleep":
                self.change_owner(backup_path, new_owner="vibflysleep")


def dummy_job(*args):
    logging.warning("Hello World")


class GenericBackupWrapper(object):
    def __init__(self, backup_job, results_dir, safe, server, regex=None, use_last_file=False):
        self._TICK = 1.0  # s
        self._BACKUP_DT = 5 * 60  # 5min
        # self._BACKUP_DT = 5
        self._results_dir = results_dir
        self._safe = safe
        self._backup_job = backup_job
        self._server = server
        self._regex = regex
        self._use_last_file = use_last_file

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
                        args.append((d, self._results_dir, self._use_last_file))

                logging.warning(args)
                logging.info("Found %s devices online" % len(args))


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
