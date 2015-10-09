#! python3

# pull in modules from this directory
import sys
import os.path
import logging
import argparse
from configparser import ConfigParser
from wsgiref.simple_server import make_server
from pyramid.config import Configurator

here = os.path.dirname(os.path.abspath(__file__))


def createPyramidConfig():

    # this example server logs verbosely
    logging.basicConfig(level="DEBUG")

    # handle config paths
    # load the site specific config file, if existing!
    siteConfigFile = os.path.join(here, "site.ini")
    siteConfig = ConfigParser()
    # read default config file first
    defaultConfigFile = os.path.join(here, 'default.ini')
    siteConfig.read_file(open(defaultConfigFile, 'rt'))

    if os.path.isfile(siteConfigFile):
        siteConfig.read([siteConfigFile])

    configDict = {}
    for sec, opts in siteConfig.items():
        for opt, val in opts.items():
            configDict["%s.%s" % (sec, opt)] = val

    config = Configurator()
    config.add_settings(configDict)

    configDict = config.get_settings()  # as cleansed by pyramid
    if configDict.get("debugtoolbar.enable", False):
        return

    if any(x.startswith("debugtoolbar") for x in configDict.keys()):
        config.include('pyramid_debugtoolbar')

    config.include("auth_view")

    return config

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)

    # get this from command line
    interface = 'localhost'
    port = 5555

    parser = argparse.ArgumentParser(description='stand-alone server for '
                                     'login module')
    parser.add_argument('--port', type=int, nargs=1, default=[port],
                        help='port number, default is %d' % port)
    parser.add_argument('--interface', type=str, nargs=1, default=[interface],
                        help=('interface, e.g. 0.0.0.0, default is %s' %
                              interface))
    args = parser.parse_args()

    config = createPyramidConfig()
    application = config.make_wsgi_app()

    httpd = make_server(host=args.interface[0],
                        port=args.port[0],
                        app=application)
    logging.info("serving at %s:%d",
                 args.interface[0],
                 args.port[0])
    httpd.serve_forever()
