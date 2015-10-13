'''
.. codeauthor: Achim
.. sectionauthor:: Achim

Provides basic login/session context functionality based on pyramid's
authorization/authentication framework.

This module is configured with two asset directories:
* the 'static_assets_login' directory
* the 'static_assets_project' directory

This module serves the first match in this list.

* /api/login and /api/logout
* /login redirects to /login/
* /login/* serves everything in static_assets_login using login.html as index
* selected resources from static_assets_project as specified by config.json
'''

import base64
import random
import hashlib
import os.path
import logging
import json

from pyramid.httpexceptions import (HTTPBadRequest, HTTPForbidden,
                                    HTTPFound, HTTPNotFound)

from pyramid.response import Response, FileResponse
from pyramid.static import static_view

# create authentication/authorization framework
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import (NO_PERMISSION_REQUIRED,
                              remember, forget,
                              Allow, Deny,
                              Authenticated, Everyone,
                              Allowed, Denied)

here = os.path.dirname(os.path.abspath(__file__))
repository_root = os.path.dirname(here)  # should be one level further down

# get these from configuration / config.json
peter_config = json.load(open(os.path.join(repository_root,
                                           "login",
                                           "config.json"),
                              "r"))

static_assets_login = os.path.join(repository_root,
                                   'login')
# that might come from peter_config
# confusingly this is the same right now!
static_assets_project = os.path.join(repository_root,
                                     'login')


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


def loginPageRedirect(request):
    return HTTPFound("/login/")


def loginAPIView(request):
    """
    :param pyramid.Request request: request POST with ``username`` and
         ``password`` as md5 hash
    :rtype: pyramid.Response
    :returns: response with session cookie in header or Forbidden for
         unrecognized credentials

    Use this view with a ``POST`` request to send ``username`` and
    ``passowrd``. A session is generated and added to the response header.
    To invalidate the session call :py:func:`logoutView` available at
    ``/api/logout``.

    By now authentication is pretty phony, the password hash has to match a
    defined string defined in :py:const:`thePassword`.

    .. note::

        Not to be confused with ``/login``, which is provided by
        :py:func:`staticAssets.app_view`.
    """

    if not ("username" in request.POST and "password" in request.POST):
        return HTTPBadRequest(explanation="username or password not supplied",
                              request=request)

    theUser = request.POST["username"]
    # todo: read out password from db

    thePassword = "tuatara"
    passwordhash = hashlib.md5()
    passwordhash.update(thePassword.encode('utf8'))

    # make sure there is some user name
    if theUser == "" or request.POST["password"] != passwordhash.hexdigest():
        return HTTPForbidden(explanation="password does not match",
                             request=request)

    response_headers = remember(request, theUser)
    response = Response(headers=response_headers)
    return response


def logoutAPIView(request):
    """
    invalidates the session when ``/api/logout`` is called.
    """
    # will logout have some username/email info?
    response_headers = forget(request)
    response = Response(headers=response_headers)
    return response


def loginPageView(request):
    # todo: assure this file is there

    return FileResponse(os.path.join(static_assets_login, "login.html"),
                        request=request)


class projectView(static_view):

    def __call__(self, context, request):
        if not request.has_permission("view"):
            return HTTPFound("/login/",
                             request=request)

        return static_view.__call__(self, context, request)


def includeme(config):
    """
    Provides the ``/api/login`` and ``/api/logout`` routes

    Reads out the session time out and initializes authentication and
    authorization.
    Configures ``pyramid.authentication.AuthTktAuthenticationPolicy``

    Todo: re-implement callback
    """

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

    config.set_root_factory(RootFactory)
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)

    # these are the API functions, serve them always
    config.add_route('login',
                     '/api/login')
    config.add_view(loginAPIView,
                    route_name="login",
                    permission=NO_PERMISSION_REQUIRED)
    config.add_route("login_w_redir",
                     '/api/login/*subpath',)
    config.add_view(loginAPIView,
                    route_name="login_w_redir",
                    permission=NO_PERMISSION_REQUIRED)
    config.add_route('logout',
                     '/api/logout')
    config.add_view(logoutAPIView,
                    route_name="logout",
                    permission=NO_PERMISSION_REQUIRED)

    # a special exception for Caleb's test:
    # loggedin.html only being served when logged in
    def loggedInView(request):
        if not request.has_permission('read'):
            return loginPageRedirect(request)
        else:
            FileResponse(static_assets_login, "loggedin.html")
    config.add_route("login.loggedin",
                     "/loggedin.html")
    config.add_view(loginPageRedirect,
                    route_name='login.loggedin')

    # this serves the login screen
    config.add_route("loginPageRedir",
                     "/login")
    config.add_view(loginPageRedirect,
                    route_name='loginPageRedir')

    config.add_route("loginPage",
                     "/login/*subpath")
    config.add_view(static_view(static_assets_login,
                                use_subpath=True),
                    route_name='loginPage')

    # generate all resource routes needed from the project folder
    # each string is a URL, which is a file or a directory being served in the
    # static_assets_project directory

    projectAssets = []  # get from peter_config

    if peter_config["showLogo"]:
        projectAssets.append(peter_config["logoPath"])
    if peter_config["customCSS"]:
        projectAssets.append(peter_config["cssPath"])

    for projectAsset in projectAssets:

        if projectAsset.startswith("/"):
            # make this relative to project assets directory
            projectAsset.lstrip("/")

        fileLocation = os.path.realpath(os.path.join(static_assets_project,
                                                     projectAsset))

        if not fileLocation.startswith(
                    os.path.realpath(static_assets_project)):
            # skip that one, it is outside the project
            logging.warn("%s is outside the project files" % projectAsset)
            continue

        if os.path.isfile(fileLocation):
            def projectFileResponse(request):
                return FileResponse(fileLocation,
                                    request=request)
            # do a file response
            config.add_route("login.projectAssetFile.%s" % projectAsset,
                             "/login/"+projectAsset)
            config.add_view(projectFileResponse,
                            route_name=("login.projectAssetFile.%s" %
                                        projectAsset))

        elif os.path.isdir(fileLocation):
            # do a file response
            projectAsset = projectAsset.rstrip("/")
            config.add_route("login.projectAssetFile.%s" % projectAsset,
                             "/login/"+projectAsset+"/*subpath")
            config.add_view(static_view(fileLocation,
                                        use_subpath=True),
                            route_name=("login.projectAssetFile.%s" %
                                        projectAsset))

    # and now a catch-all
    config.add_route("protectedProject",
                     "/*subpath")
    config.add_view(projectView(static_assets_project,
                                use_subpath=True),
                    route_name="protectedProject")