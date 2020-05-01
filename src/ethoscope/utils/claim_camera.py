import picamera
import time
import logging
import os
import sys
import signal

logging.basicConfig(level=logging.INFO)

pidfile = "/var/run/picamera/picamera.pid"

def remove_pidfile(pidfile=pidfile):
    logging.info("Removing pidfile")
    os.unlink(pidfile)

def create_pidfile(pidfile=pidfile):
    pid = str(os.getpid())
    directory = "/var/run/picamera/"
    os.makedirs(directory, exist_ok=True)

    if os.path.isfile(pidfile):
        logging.warning(f"An existing pidfile is detected in {pidfile}.")

        with open(pidfile, 'r') as fh:
            pid = fh.readline().strip("\n")
            logging.warning(f"Killing the process with the PID in that file...")
            os.kill(int(pid), signal.SIGTERM)

        remove_pidfile(pidfile)


    with open(pidfile, 'w') as fh:
        logging.info(f"Writing PID {pid} to pidfile {pidfile}")
        fh.write(str(pid))



def kill_all_instances():

    #ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
    ps = subprocess.Popen(['ps', '-ef'], stdout=subprocess.PIPE)
    output = subprocess.check_output(('grep', 'device_server\.py'), stdin=ps.stdout)
    ps.wait()
    output_split = output.decode("utf-8").split('\n')
    output_split = [e for e in output_split if e != '']
    [print(e) for e in output_split]

    pids = []
    for e in output_split:
        f = [e for e in e.split(' ') if e != '']
        pid = int(f[1])
        pids.append(pid)

    pids_to_remove = pids[1:]
    for pid in pids_to_remove:
        logging.warning('Sending SIGTERM to {}'.format(pid))
        os.kill(pid, signal.SIGTERM) #or signal.SIGKILL
    else:
        logging.info('No two extra processes found')

    return len(pids_to_remove)



def claim_camera():
    create_pidfile()
    capture = picamera.PiCamera()

    return capture

