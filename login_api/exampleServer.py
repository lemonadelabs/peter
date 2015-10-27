#! python3


# pull in modules from this directory
import sys
import os.path
import logging
import argparse
from configparser import ConfigParser
from wsgiref.simple_server import make_server
from pyramid.config import Configurator

import base64
import random
import hashlib

from pyramid.static import static_view

# create authentication/authorization framework
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import Allow, Authenticated

here = os.path.dirname(os.path.abspath(__file__))
# expected to be one level further down
repository_root = os.path.dirname(here)


def credentialsCheck(user, passwordHash):

    thePassword = "tuatara"
    passwordhash = hashlib.md5()
    passwordhash.update(thePassword.encode('utf8'))

    if (user == "" or passwordHash != passwordhash.hexdigest()):
        return None

    return user


# todo: has to be implemented properly
def groupfinder(userid, request):
    """
    future use: product managers, general managers,
    supplier logins, developer accounts
    """
    return []


class RootFactory:
    """
    future use: more fine-grained access
    """
    __acl__ = [(Allow, Authenticated, 'view'),
               ]

    def __init__(self, request):
        pass


class projectView(static_view):
    """
    project static file server with permission check and redirect to
    login if not logged in.
    """

    def __init__(self, p):
        self.loginRedirect = p.loginPageRedirect
        self.minPermissions = p.minimalPermissions
        static_view.__init__(self,
                             root_dir=p.static_assets_project,
                             use_subpath=True)

    def __call__(self, context, request):
        if not request.has_permission(self.minPermissions,
                                      context=context):
            return self.loginRedirect(request)

        return static_view.__call__(self, context, request)


def createAuthFramework(config):

    settings = config.get_settings()
    # no timeout is default
    timeout = settings.get("authentication.session_timeout", 3600)
    if timeout in ["None", "null", ""]:
        timeout = None
    reissue_timeout = None
    if timeout is not None:
        timeout = float(timeout)
        reissue_timeout = float(timeout)/10.0

    hashSecret = settings.get("authentication.secret", None)
    if hashSecret is None:
        # generate one as random
        hashSecret = str(base64.b85encode(bytes([random.randrange(0, 256)
                                                 for _ in range(12)])),
                         'utf-8')

    authn_policy = AuthTktAuthenticationPolicy(hashSecret,
                                               hashalg='sha512',
                                               callback=groupfinder,
                                               timeout=timeout,
                                               reissue_time=reissue_timeout)
    authz_policy = ACLAuthorizationPolicy()

    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)

    static_assets_login = os.path.join(repository_root,
                                       'login')
    # that might come from peter_config
    # confusingly this is the same right now!
    static_assets_project = os.path.join(repository_root,
                                         'login')

    from peter import peter
    p = peter(config,
              os.path.join(static_assets_login, "config.json"),
              static_assets_login,
              static_assets_project,
              credentialsCheck,  # hand over authentication method
              "view")

    # and here the API calls
    # todo

    # and now a catch-all which serves the project's static files
    config.add_route("protectedProject",
                     "/*subpath",
                     factory=RootFactory)
    config.add_view(projectView(p),
                    route_name="protectedProject")


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

    # now setup the authentication framework
    # now load the peter project
    createAuthFramework(config)

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
