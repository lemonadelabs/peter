#! python3

# pull in modules from this directory
import sys
import os.path
import logging
import argparse
from configparser import ConfigParser
from wsgiref.simple_server import make_server
from pyramid.response import FileResponse
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.config import Configurator

here = os.path.dirname(os.path.abspath(__file__))
repository_root = os.path.dirname(here)  # should be one level further down
static_assets_login = os.path.join(repository_root, 'build')


def app_view(request):
    """
    :rtype: pyramid.Respone

    provide non-asset or image requests, redirects to ``/login`` if no valid
    session context established. (to be fixed!)
    """

    # assume this is the path for the application
    if request.path == "/" or request.path == "/index.html":
        # decide whether authenticated or not except for /login
        if not request.has_permission('view') and request.path != "/login":
            return HTTPFound(location="/login", request=request)

        indexPath = os.path.join(static_assets_login, "index.html")
        if os.path.isfile(indexPath):
            return FileResponse(indexPath,
                                request=request)
        else:
            return HTTPNotFound(request=request)

    pathRequested = os.path.join(static_assets_login, request.path.lstrip("/"))

    # secure against path traversal with .. or similar
    if pathRequested.startswith(static_assets_login):
        if os.path.isfile(pathRequested):
            return FileResponse(pathRequested,
                                request=request)
        else:
            # might not be there
            return HTTPNotFound(request=request)
    else:
        # invalid path
        return HTTPNotFound(request=request)


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

    config.include("auth_view", route_prefix="/api")

    config.add_route('simone_app', '*subpath')
    config.add_view(app_view,
                    route_name='simone_app')
    config.add_route('simone_app2', '/')
    config.add_view(app_view,
                    route_name='simone_app2')

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
