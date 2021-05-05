import logging
import time
import threading

import bottle

from ethoscope.hardware.interfaces.optomotor import SleepDepriver


class SDServer(threading.Thread):

    def __init__(self, *args, port=9001, debug=True, **kwargs):

        self._port = port
        self._debug = debug
        self.sd = SleepDepriver(do_warm_up=False)
        super().__init__(*args, **kwargs)


    def run(self):
    
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
            bottle.server_names["cherrypy"] = CherootServer(host='0.0.0.0', port=self._port)
            logging.warning("Cherrypy version is bigger than 9, change to cheroot server")
            pass
        #########
        
        app = self.routeapp()
        bottle.run(app, host='0.0.0.0', port=self._port, debug=self._debug, server=SERVER)
    
    #@api.post("/activate")
    def activate(self):
        data = bottle.request.json
        duration  = int(data["duration"])
    
        if type(data["channels"]) is int:
            channels = [data["channels"]]
        elif type(data["channels"]) is list:
            channels = data["channels"]
        else:
            logging.warning("Pass int or list in channel field")
            return 1 
    
        for channel in channels:
            self.sd.activate(channel=channel, duration=duration)
        return 0

    activate.post = "/activate"


    def routeapp(app):

        for kw in dir(app):
            attr = getattr(app, kw)
            if hasattr(attr, 'route'):
                bottle.route(attr.route)(attr)

            if hasattr(attr, 'post'):
                bottle.post(attr.post)(attr)
