__author__ = 'luis'

import logging
import traceback
from optparse import OptionParser
import subprocess
import json
import os
import glob
from ethoscope.web_utils.helpers import get_machine_id
logging.basicConfig(level=logging.INFO)

#from bottle import Bottle, ServerAdapter, request, server_names

import socket
from zeroconf import ServiceInfo, Zeroconf

PORT=9000

def main():

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
        
        
        logging.warning("Waiting for a network connection")
        address = False
        while address is False:
            try:
                #address = socket.gethostbyname(hostname+".local")
                address = socket.gethostbyname(hostname)
                #this returns something like '192.168.1.4' - when both connected, ethernet IP has priority over wifi IP
            except:
                pass
                #address = socket.gethostbyname(hostname)
                #this returns '127.0.1.1' and it is useless
            
            
        serviceInfo = ServiceInfo("_ethoscope._tcp.local.",
                        uid + "._ethoscope._tcp.local.",
                        address = socket.inet_aton(address),
                        port = PORT,
                        properties = {
                            'version': '0.0.1',
                            'id_page': '/id',
                            'user_options_page': '/user_options',
                            'static_page': '/static',
                            'controls_page': '/controls',
                            'user_options_page': '/user_options'
                        } )
        zeroconf = Zeroconf()
        zeroconf.register_service(serviceInfo)
        logging.info('Device registered')

    except OSError as e:
        logging.error(e)
        logging.error(traceback.format_exc())
        for i in range(9):
            time.sleep(10)
            return main()

    except Exception as e:
        try:
            logging.info('Device not registered')
            logging.error(e)
            logging.error(traceback.format_exc())
            zeroconf.unregister_service(serviceInfo)
            zeroconf.close()
        except Exception:
            pass

        close(1)

    finally:
        try:
            zeroconf.unregister_service(serviceInfo)
            zeroconf.close()
        except:
            pass
        close()


def close(exit_status=0):
    os._exit(exit_status)


