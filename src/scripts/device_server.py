__author__ = 'luis'

import argparse
import glob
import json
import logging
import os
import subprocess
import traceback

import bottle
import socket
from zeroconf import ServiceInfo, Zeroconf


from ethoscope.web_utils.control_thread import ControlThread
from ethoscope.web_utils.helpers import *
from ethoscope.web_utils.record import ControlThreadVideoRecording

#from bottle import Bottle, ServerAdapter, request, server_names

try:
    from cheroot.wsgi import Server as WSGIServer
except ImportError:
    from cherrypy.wsgiserver import CherryPyWSGIServer as WSGIServer


api = bottle.Bottle()

tracking_json_data = {}
recording_json_data = {}
update_machine_json_data = {}
ETHOSCOPE_DIR = None

def list_options(category):
    """
    Return a list of str with the names of the classes that can be passed
    for a given category.
    """
    return [cls.__name__ for cls in ControlThread._option_dict[category]['possible_classes']]


class WrongMachineID(Exception):
    pass


def error_decorator(func):
    """
    A simple decorator to return an error dict so we can display it the ui
    """
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(traceback.format_exc())
            return {'error': traceback.format_exc()}
    return func_wrapper

@api.route('/upload/<id>', method='POST')
def do_upload(id):

    if id != machine_id:
        raise WrongMachineID

    upload = bottle.request.files.get('upload')
    name, ext = os.path.splitext(upload.filename)

    if ext in ('.mp4', '.avi'):
        category = 'video'
    elif ext in ('.jpg', '.png'):
        category = 'images'
    elif ext in ('.msk'):
        category = 'masks'
    else:
        return {'result' : 'fail', 'comment' : "File extension not allowed. You can upload only movies, images, or masks"}

    save_path = os.path.join(ETHOSCOPE_UPLOAD, "{category}".format(category=category))
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    file_path = "{path}/{file}".format(path=save_path, file=upload.filename)
    upload.save(file_path)
    return { 'result' : 'success', 'path' : file_path }

@api.route('/static/<filepath:path>')
def server_static(filepath):
    return bottle.static_file(filepath, root="/")

@api.route('/download/<filepath:path>')
def server_static_download(filepath):
    return bottle.static_file(filepath, root="/", download=filepath)

@api.get('/id')
@error_decorator
def name():
    return {"id": control.info["id"]}

@api.get('/make_index')
@error_decorator
def make_index():
    index_file = os.path.join(ETHOSCOPE_DIR, "index.html")
    all_video_files = [y for x in os.walk(ETHOSCOPE_DIR) for y in glob.glob(os.path.join(x[0], '*.h264'))]
    all_pickle_files = [y for x in os.walk(ETHOSCOPE_DIR) for y in glob.glob(os.path.join(x[0], '*.pickle'))]
    all_files = all_video_files + all_pickle_files
    with open(index_file, "w") as index:
        for f in all_files:
            index.write(f + "\n")
    return {}

@api.post('/rm_static_file/<id>')
@error_decorator
def rm_static_file(id):
    global control
    global record

    data = bottle.request.body.read()
    data = json.loads(data)
    file_to_del = data["file"]
    if id != machine_id:
        raise WrongMachineID

    if file_in_dir_r(file_to_del, ETHOSCOPE_DIR ):
        os.remove(file_to_del)
    else:
        msg = "Could not delete file %s. It is not allowed to remove files outside of %s" % (file_to_del, ETHOSCOPE_DIR)
        logging.error(msg)
        raise Exception(msg)
    return data

@api.post('/update/<id>')
def update_machine_info(id):
    '''
    Updates the private machine informations
    '''
    if id != machine_id:
        raise WrongMachineID

    data = bottle.request.json
    update_machine_json_data.update(data['machine_options']['arguments'])

    if update_machine_json_data['node_ip'] != get_machine_info(id)['etc_node_ip']:
        set_etc_hostname(update_machine_json_data['node_ip'])

    if int(update_machine_json_data['etho_number']) != int(get_machine_info(id)['machine-number']):
        set_machine_name(update_machine_json_data['etho_number'])
        set_machine_id(update_machine_json_data['etho_number'])

    set_WIFI(ssid=update_machine_json_data['ESSID'], wpakey=update_machine_json_data['Key'])

    return get_machine_info(id)


@api.post('/controls/<id>/<action>')
@error_decorator
def controls(id, action):
    global control
    global record
    if id != machine_id:
        raise WrongMachineID

    if action == 'start':
        data = bottle.request.json
        tracking_json_data.update(data)

        control = None
        control = ControlThread(machine_id=machine_id,
                                name=machine_name,
                                version=version,
                                ethoscope_dir=ETHOSCOPE_DIR,
                                data=tracking_json_data)

        control.start()
        return info(id)

    elif action in ['stop', 'close', 'poweroff', 'reboot', 'restart']:

        if control.info['status'] in ['running', 'recording', 'streaming'] :
            logging.info("Stopping monitor")
            control.stop()
            logging.info("Joining monitor")
            control.join()
            logging.info("Monitor joined")
            logging.info("Monitor stopped")

        if action == 'close':
            close()

        if action == 'poweroff':
            logging.info("Stopping monitor due to poweroff request")
            logging.info("Powering off Device.")
            subprocess.call('poweroff')

        if action == 'reboot':
            logging.info("Stopping monitor due to reboot request")
            logging.info("Powering off Device.")
            subprocess.call('reboot')

        if action == 'restart':
            logging.info("Restarting service")
            subprocess.call(['systemctl', 'restart', 'ethoscope_device'])


        return info(id)

    elif action in ['start_record', 'stream']:
        data = bottle.request.json
        recording_json_data.update(data)
        logging.warning("Recording or Streaming video, data is %s" % str(data))
        control = None
        control = ControlThreadVideoRecording(machine_id=machine_id,
                                              name=machine_name,
                                              version=version,
                                              ethoscope_dir=ETHOSCOPE_DIR,
                                              data=recording_json_data)

        control.start()
        return info(id)

    else:
        raise Exception("No such action: %s" % action)

@api.get('/data/listfiles/<category>/<id>')
@error_decorator
def list_data_files(category, id):
    '''
    provides a list of files in the ethoscope data folders, that were either uploaded or generated
    '''
    if id != machine_id:
        raise WrongMachineID

    path = os.path.join(ETHOSCOPE_UPLOAD, category)

    if os.path.exists(path):
        return {'filelist' : [{'filename': i, 'fullpath' : os.path.abspath(os.path.join(path,i))} for i in os.listdir(path)]}

    return {}


@api.get('/machine/<id>')
@error_decorator
def get_machine_info(id):
    """
    This is information about the ethoscope that is not changing in time
    such as hardware specs and configuration parameters
    partitions includes the Use% of each partition in the RPi)
    """

    if id is not None and id != machine_id:
        raise WrongMachineID

    machine_info = {}
    machine_info['node_ip'] = bottle.request.environ.get('HTTP_X_FORWARDED_FOR') or bottle.request.environ.get('REMOTE_ADDR')

    try:
        machine_info['etc_node_ip'] = get_etc_hostnames()[NODE]
    except:
        machine_info['etc_node_ip'] = "not set"

    machine_info['knows_node_ip'] = (machine_info['node_ip'] == machine_info['etc_node_ip'])
    machine_info['hostname'] = os.uname()[1]

    machine_info['machine-name'] = get_machine_name()

    try:
        machine_info['machine-number'] = int (machine_info['machine-name'].split("_")[1])
    except:
        machine_info['machine-number'] = 0


    machine_info['machine-id'] = get_machine_id()
    machine_info['kernel'] = os.uname()[2]
    machine_info['pi_version'] = pi_version()
    try:
        machine_info['WIFI_SSID'] = get_WIFI()['ESSID']
    except:
        machine_info['WIFI_SSID'] = "not set"
    try:
        machine_info['WIFI_PASSWORD'] = get_WIFI()['Key']
    except:
        machine_info['WIFI_PASSWORD'] = "not set"

    machine_info['SD_CARD_AGE'] = get_SD_CARD_AGE()
    machine_info['partitions'] = get_partition_infos()

    return machine_info


@api.get('/data/<id>')
@error_decorator
def info(id):
    """
    This is information that is changing in time as the machine operates, such as FPS during tracking, CPU temperature etc
    """

    info = {}
    if machine_id != id:
        logging.warning(f"machine_id is {machine_id} but id is {id}")
        raise WrongMachineID

    if control is not None:
        info = control.info

    info["current_timestamp"] = bottle.time.time()
    info["CPU_temp"] = get_core_temperature()
    info["loadavg"] = get_loadavg()
    return info

@api.get('/user_options/<id>')
@error_decorator
def user_options(id):
    '''
    Passing back options regarding the capabilities of the device
    '''
    if machine_id != id:
        raise WrongMachineID



    return {
        "tracking":ControlThread.user_options(),
        "recording":ControlThreadVideoRecording.user_options(),
        "streaming": {},
        "update_machine": { "machine_options": [{"overview": "Machine information that can be set by the user",
                            "arguments": [
                                {"type": "number", "name":"etho_number", "description": "An ID number (1-999) unique to this ethoscope","default": get_machine_info(id)['machine-number'] },
                                {"type": "str", "name":"node_ip", "description": "The IP address that you want to record as the node (do not change this value unless you know what you are doing!)","default": get_machine_info(id)['node_ip']},
                                {"type": "str", "name":"ESSID", "description": "The name of the WIFI SSID","default": get_machine_info(id)['WIFI_SSID'] },
                                {"type": "str", "name":"Key", "description": "The WPA password for the WIFI SSID","default": get_machine_info(id)['WIFI_PASSWORD'] }],
                            "name" : "Ethoscope Options"}],

                               } }

@api.get('/data/log/<id>')
@error_decorator
def get_log(id):
    output = "No log available"
    try:
        with os.popen('journalctl -u ethoscope_device.service -rb') as p:
            output = p.read()

    except Exception as e:
        logging.error(traceback.format_exc())

    return {'message' : output}


def close(exit_status=0):
    global control
    if control is not None and control.is_alive():
        control.stop()
        control.join()
        control=None
    else:
        control = None
    os._exit(exit_status)

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

#======================================================================================================================#
#############
### CLASSS TO BE REMOVED IF BOTTLE CHANGES TO 0.13
############
class CherootServer(bottle.ServerAdapter):
    def run(self, handler): # pragma: no cover
        from cheroot import wsgi
        from cheroot.ssl import builtin
        self.options['bind_addr'] = (self.host, self.port)
        self.options['wsgi_app'] = handler
        certfile = self.options.pop('certfile', None)
        keyfile = self.options.pop('keyfile', None)
        chainfile = self.options.pop('chainfile', None)
        server = wsgi.Server(**self.options)
        if certfile and keyfile:
            server.ssl_adapter = builtin.BuiltinSSLAdapter(
                    certfile, keyfile, chainfile)
        try:
            server.start()
        finally:
            server.stop()
#############

if __name__ == '__main__':

    ETHOSCOPE_DIR = "/ethoscope_data/results"
    ETHOSCOPE_UPLOAD = "/ethoscope_data/upload"
    ETHOSCOPE_VIDEOS = "/ethoscope_data/videos"

    ap = argparse.ArgumentParser()

    ap.add_argument("--run", dest="run", default=False, help="Runs tracking directly", action="store_true")
    ap.add_argument(
        "--use-wall-clock", dest="use_wall_clock", default=False,
        help="For offline analysis, whether to use the system's time (True) or the video time (False)", action="store_true"
    )
    ap.add_argument("-s", "--stop-after-run", dest="stop_after_run", default=False, help="When -r, stops immediately after. otherwise, server waits", action="store_true")
    ap.add_argument("-v", "--record-video", dest="record_video", default=False, help="Records video instead of tracking", action="store_true")
    ap.add_argument("-j", "--json", dest="json", default=None, help="A JSON config file")
    ap.add_argument("-p", "--port", dest="port", type=int, default=9000, help="port")
    ap.add_argument("-n", "--node", dest="node", default="node", help="The hostname of the computer running the node")
    ap.add_argument("-e", "--results-dir", dest="results_dir", default=ETHOSCOPE_DIR, help="Where temporary result files are stored")
    ap.add_argument("--video-results-dir", dest="video_results_dir", default=ETHOSCOPE_VIDEOS, help="Where mp4 video files are stored")
    ap.add_argument("-D", "--debug", dest="debug", default=False, help="Shows all logging messages", action="store_true")

    ap.add_argument("-i", "--input", help="Input mp4 file", type=str)
    ap.add_argument("-o", "--output", help="Resulting sqlite3 db file", type=str)
    ap.add_argument("-c", "--camera", help="Name of camera class", default="FSLVirtualCamera", type=str, choices=list_options("camera"))
    ap.add_argument("--machine_id", type=str, required=False)
    ap.add_argument("--name", type=str, default=None)
    ap.add_argument("-r", "--roi-builder", dest="roi_builder", type=str, default="FSLSleepMonitorWithTargetROIBuilder", choices=list_options("roi_builder"))
    ap.add_argument("--tracker", type=str, choices=list_options("tracker"))
    ap.add_argument("-t", "--target-coordinates-file", dest="target_coordinates_file", type=str, required=False, default="/etc/target_coordinates.conf")
    ap.add_argument("--rois-pickle-file", dest="rois_pickle_file", type=str, required=False, default="rois.pickle")
    ap.add_argument("-d", "--drop-each", dest="drop_each", type=int, default=1)
    ap.add_argument("-a", "--address", type=str, default=None)

    ARGS = vars(ap.parse_args())

    PORT = ARGS["port"]

    while is_port_in_use(PORT):
        logging.warning(f"port {PORT} is in use. Trying port {PORT+1}")
        PORT += 1

    DEBUG = ARGS["debug"]
    NODE = ARGS["node"]
    ETHOSCOPE_DIR = ARGS["results_dir"]
    ETHOSCOPE_VIDEOS = ARGS["video_results_dir"]
    VERSION = get_git_version()
    version = VERSION
    DROP_EACH = ARGS["drop_each"]
    ADDRESS = ARGS["address"]

    if ARGS["name"] is None:
        NAME = get_machine_name()
    else:
        NAME = ARGS["name"]

    machine_name = NAME

    if ARGS["machine_id"] is None:
        MACHINE_ID = get_machine_id()
    else:
        MACHINE_ID = ARGS["machine_id"]
    # this is overriden if --run. see below if if ARGS["run"]
    machine_id = MACHINE_ID


    if ARGS["json"]:
        with open(ARGS["json"]) as f:
            json_data = json.loads(f.read())
    else:
        json_data = {}


    if ARGS["record_video"]:
        recording_json_data = json_data

        control = ControlThreadVideoRecording(machine_id=machine_id,
                                              name=machine_name,
                                              version=version,
                                              ethoscope_dir=ETHOSCOPE_DIR,
                                              data=recording_json_data)

    elif ARGS["run"]:
        # from folder in ethoscope_data/videos
        # in case ETHOSCOPE_VIDEOS has a trailing /, remove any / on the left
        MACHINE_ID = ARGS["input"].replace(ETHOSCOPE_VIDEOS, "").lstrip("/").split("/")[0]
        # from filename
        machine_id = ARGS["input"].split("/")[::-1][0].split("_")[3]
        assert MACHINE_ID == machine_id

        if ARGS["output"] is None:
            DATE = ARGS["input"].split("/")[::-1][1]
            OUTPUT = os.path.join(ETHOSCOPE_DIR, MACHINE_ID, NAME, DATE, DATE + "_" + MACHINE_ID + ".db")
        else:
            OUTPUT = ARGS["output"]


        logging.info(OUTPUT)


        data = {
            "camera":
                {"name": ARGS["camera"], "args": (ARGS["input"],), "kwargs": {"use_wall_clock": ARGS["use_wall_clock"], "drop_each": ARGS["drop_each"]}},
            "result_writer":
                {"name": "SQLiteResultWriter", "kwargs": {"path": OUTPUT, "take_frame_shots": True}},
            "roi_builder":
                {"name": ARGS["roi_builder"], "kwargs": {"target_coordinates_file": ARGS["target_coordinates_file"], "rois_pickle_file": ARGS["rois_pickle_file"]}},
            "tracker":
                {"name": ARGS["tracker"], "kwargs": {}}
        }

        json_data.update(data)
        tracking_json_data = json_data

    control = ControlThread(MACHINE_ID, NAME, VERSION, ethoscope_dir=ETHOSCOPE_DIR, data=tracking_json_data, verbose=True)

    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
        logging.info("Logging using DEBUG SETTINGS")

    if ARGS["stop_after_run"]:
         control.set_evanescent(True) # kill program after first run

    if ARGS["run"] or control.was_interrupted:
        control.start()

#    try:
#        run(api, host='0.0.0.0', port=port, server='cherrypy',debug=ARGS["debug"])

    try:
        # Register the ethoscope using zeroconf so that the node knows about it.
        # I need an address to register the service, but I don't understand which one (different
        # interfaces will have different addresses). The python module zeroconf fails if I don't
        # provide one, and the way it gets supplied doesn't appear to be IPv6 compatible. I'll put
        # in whatever I get from "gethostbyname" but not trust that in the code on the node side.


        # we include the machine-id together with the hostname to make sure each device is really unique
        # moreover, we will burn the ETHOSCOPE_000 img with a non existing /etc/machine-id file
        # to make sure each burned image will get a unique machine-id at the first boot

        hostname = socket.gethostname()
        uid = "%s-%s" % ( hostname, get_machine_id() )

        address = False
        logging.warning("Waiting for a network connection")

        while address is False:
            try:
                #address = socket.gethostbyname(hostname+".local")
                if ADDRESS is None:
                    address = socket.gethostbyname(hostname)
                else:
                    address = ADDRESS
                #this returns something like '192.168.1.4' - when both connected, ethernet IP has priority over wifi IP
            except:
                pass
                #address = socket.gethostbyname(hostname)
                #this returns '127.0.1.1' and it is useless


        logging.info(f"UID {uid}")
        logging.info(f"Address {address}")
        logging.info(f"PORT {PORT}")
        serviceInfo = ServiceInfo("_ethoscope._tcp.local.",
                        uid + "._ethoscope._tcp.local.",
                        address=socket.inet_aton(address),
                        port=PORT,
                        properties={
                            'version': '0.0.1',
                            'id_page': '/id',
                            'user_options_page': '/user_options',
                            'static_page': '/static',
                            'controls_page': '/controls',
                            'user_options_page': '/user_options'
                        })
        zeroconf = Zeroconf()
        zeroconf.register_service(serviceInfo)

        ####### THIS IS A BIG MESS AND NEEDS TO BE FIXED. To be remove when bottle changes to version 0.13

        SERVER = "cheroot"
        try:
            #This checks if the patch has to be applied or not. We check if bottle has declared cherootserver
            #we assume that we are using cherrypy > 9
            from bottle import CherootServer
        except:
            #Trick bottle to think that cheroot is actulay cherrypy server, modifies the server_names allowed in bottle
            #so we use cheroot in background.
            SERVER = "cherrypy"
            bottle.server_names["cherrypy"] = CherootServer(host='0.0.0.0', port=PORT)
            logging.warning("Cherrypy version is bigger than 9, change to cheroot server")
            pass
        #########

        bottle.run(api, host='0.0.0.0', port=PORT, debug=DEBUG, server=SERVER)

    except Exception as e:
        logging.error(traceback.format_exc())
        try:
            zeroconf.unregister_service(serviceInfo)
            zeroconf.close()
        except:
            pass
        close(1)

    finally:
        try:
            zeroconf.unregister_service(serviceInfo)
            zeroconf.close()
        except:
            pass
        close()
