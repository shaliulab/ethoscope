import logging
import time
import bottle
from ethoscope.hardware.interfaces.optomotor import SleepDepriver


api = bottle.Bottle()
sd = SleepDepriver(do_warm_up=False)
PORT=9001
DEBUG=True


def run(api):

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
        bottle.server_names["cherrypy"] = CherootServer(host='0.0.0.0', port=PORT)
        logging.warning("Cherrypy version is bigger than 9, change to cheroot server")
        pass
    #########
    
    bottle.run(api, host='0.0.0.0', port=PORT, debug=DEBUG, server=SERVER)

@api.post("/activate")
def activate():
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
        sd.activate(channel=channel, duration=duration)
        time.sleep(2)
    return 0


run(api)
