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
import datetime

# create authentication/authorization framework
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import Allow, Authenticated

here = os.path.dirname(os.path.abspath(__file__))
# expected to be one level further down
repository_root = os.path.dirname(here)

tokenStorage = {}

passwordhashHex = None
api_key = ""  # readout from config file!


def credentialsCheck(user, passwordHash):
    global passwordhashHex

    if (user == "" or passwordHash != passwordhashHex):
        return None

    return user


def checkUserEmail(username, email):
    """
    the mock implementation does approve emails with start with the username
    """
    if email.lower().startswith(username.lower()):
        return True
#    if username == "achim" and email=="achim.gaedke@lemonadelabs.io":
#        return True
    return False


def resetPassword(username, pwdHash):
    logging.info("resetting password for user %s" % username)


def removeExpiredTokens():
    global tokenStorage
    now = datetime.datetime.now()
    expTokens = [t for t, (_, _, e) in tokenStorage.items()
                 if e < now]
    for e in expTokens:
        try:
            del tokenStorage[e]
        except KeyError:
            pass


def storeToken(token, purpose, username, expiryDate):
    global tokenStorage
    tokenStorage[token] = (purpose, username, expiryDate)
    removeExpiredTokens()


def retreiveToken(token):
    global tokenStorage
    removeExpiredTokens()
    return tokenStorage.get(token, None)


def invalidateToken(token):
    global tokenStorage
    try:
        del tokenStorage[token]
    except KeyError:
        pass
    removeExpiredTokens()


def sendPasswordResetEmail(username, email, tokenURL):
    global api_key

    # find out first and last name

    subject = "Password Reset for Peter ExampleServer"
    text = "Hello %s!\n\nPlease reset your password on page %s." % (username,
                                                                    tokenURL)
    email = email
    fullname = username

    if not api_key:
        logging.info("sending no password reset email to %s" % email)
        logging.info("URL: "+tokenURL)
        return

    # https://mandrillapp.com/api/docs/messages.python.html#method=send
    import mandrill
    try:
        mandrill_client = mandrill.Mandrill(api_key)
        message = {'auto_html': True,
                   'from_email': 'peter-test@lemonadelabs.io',
                   'from_name': 'peter-test@lemonadelabs.io',
                   'headers': {'Reply-To': 'peter-test@lemonadelabs.io'},
                   'subject': subject,
                   'text': text,
                   'to': [{'email': email,
                           'name': fullname,
                           'type': 'to'}],
                   'url_strip_qs': None}
        result = mandrill_client.messages.send(message=message,
                                               async=False,
                                               ip_pool='Main Pool',
                                               )
        # do something with the result?!
        del result
    except mandrill.Error as e:
        # Mandrill errors are thrown as exceptions
        logging.error('A mandrill error occurred: %s - %s' %
                      (e.__class__, e))
        raise


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
                                         'example_external_project')

    from peter import peter
    p = peter(config,
              static_assets_login,
              static_assets_project,
              checkUserPassword=credentialsCheck,
              checkUserEmail=checkUserEmail,
              sendPasswordResetEmail=sendPasswordResetEmail,
              setNewPasswordHash=resetPassword,
              storeRequestToken=storeToken,
              retreiveRequestToken=retreiveToken,
              deleteRequestToken=invalidateToken,
              projectMinPermissions="view"
              )

    # and now a catch-all which serves the project's static files
    config.add_route("protectedProject",
                     "/*subpath",
                     factory=RootFactory)
    config.add_view(p.staticAssetsProjectView,
                    route_name="protectedProject")


def createPyramidConfig():
    global api_key
    global passwordhashHex

    # this example server logs verbosely
    logging.basicConfig(level="DEBUG")

    siteConfig = ConfigParser()
    # read default config file first
    defaultConfigFile = os.path.join(here, 'default.ini')
    siteConfig.read_file(open(defaultConfigFile, 'rt'))

    # handle config paths
    # load the site specific config file, if existing!
    siteConfigFile = os.path.join(here, "site.ini")
    if os.path.isfile(siteConfigFile):
        siteConfig.read([siteConfigFile])

    configDict = {}
    for sec, opts in siteConfig.items():
        for opt, val in opts.items():
            configDict["%s.%s" % (sec, opt)] = val

    config = Configurator()
    config.add_settings(configDict)
    configDict = config.get_settings()  # as cleansed by pyramid

    # setup the mandrillapp email access
    api_key = configDict.get("mandrillapp.api_key", None)
    if api_key:
        logging.debug("got mandrillapp api_key '%s'" % api_key)
    else:
        logging.debug("got no mandrillapp api_key")

    # load the initial password from the configuration
    passwordhashHex = configDict.get("peterexample.initial_pwd", "")
    logging.debug("password hash from config file is '%s'" % passwordhashHex)

    # get the debug toolbar if specified.
    if configDict.get("debugtoolbar.enable", False):
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
