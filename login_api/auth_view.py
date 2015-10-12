'''
.. codeauthor: Achim
.. sectionauthor:: Achim

Provides basic login/session context functionality based on pyramid's
authorization/authentication framework.
'''

import base64
import random
import hashlib
import os.path
import logging

from pyramid.httpexceptions import (HTTPBadRequest, HTTPForbidden,
                                    HTTPFound, HTTPNotFound)

from pyramid.response import Response, FileResponse

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
static_assets_login = os.path.join(repository_root,
                                   'build')


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
    """
    login.html might need resources from this site, these should be served
    instead of being redirected as well. What are these resources?
    this is configurable in config.json and is a list of paths in
    build/config.json .

    These paths are relative to the location of the index.html file
    customCSS and logoPath if the customCSS and showLogo are True respectively.

    .. code-block:: json

    {
      "product":"Example Product",
      "customCSS" : false,
      "cssPath" : "css/custom.css",
      "showLogo" : true,
      "logoPath" : "images/logo.svg",
      "successURL" : "/"
    }
    """
    logging.debug("loginPageView view")

    if request.has_permission("view") is Allowed:
        return HTTPFound("/")  # success url

    indexPath = os.path.join(static_assets_login, "index.html")
    if os.path.isfile(indexPath):
        return FileResponse(indexPath,
                            content_type="text/html",
                            request=request)
    else:
        return HTTPNotFound(request=request)


def loginPageResources(request):
    logging.debug("loginPageResources view")
    if request.path == "/css/custom.css":
        cssPath = os.path.join(static_assets_login, "css/custom.css")
        if os.path.isfile(cssPath):
            return FileResponse(cssPath,
                                request=request)
        else:
            return HTTPNotFound(request=request)
    elif request.path == "/images/logo.svg":
        logoPath = os.path.join(static_assets_login, "images/logo.svg")
        if os.path.isfile(logoPath):
            return FileResponse(logoPath,
                                request=request)
        else:
            return HTTPNotFound(request=request)
    elif request.path == "/config.json":
        configPath = os.path.join(static_assets_login, "config.json")
        if os.path.isfile(configPath):
            return FileResponse(configPath,
                                request=request)
        else:
            return HTTPNotFound(request=request)
    else:
        return HTTPForbidden(request=request)


def app_view(request):
    """
    :rtype: pyramid.Respone

    provide non-asset or image requests, redirects to ``/login`` if no valid
    session context established. (to be fixed!)
    """
    logging.debug("app_view view")

    if request.has_permission("view") is not Allowed:
        return HTTPFound(request=request, location="/login.html")

    # assume this is the path for the application
    if request.path == "/" or request.path == "/index.html":

        indexPath = os.path.join(static_assets_login, "index.html")
        if os.path.isfile(indexPath):
            return FileResponse(indexPath,
                                content_type="text/html",
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

    # this serves the login screen
    config.add_route("loginPage",
                     "/login.html")
    config.add_view(loginPageView,
                    route_name='loginPage')
    config.add_route("loginPageCSS",
                     "/css/custom.css")
    config.add_view(loginPageResources,
                    route_name='loginPageCSS')
    config.add_route("loginPageLogo",
                     "/images/logo.svg")
    config.add_view(loginPageResources,
                    route_name='loginPageLogo')
    config.add_route("loginPageConfig",
                     "/config.json")
    config.add_view(loginPageResources,
                    route_name='loginPageConfig')

    # that serves the application if permissions granted!
    config.add_route('simone_app',
                     '*subpath')
    config.add_view(app_view,
                    route_name='simone_app')
    config.add_route('simone_app2',
                     '/')
    config.add_view(app_view,
                    route_name='simone_app2')
