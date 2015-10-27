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


import logging
import json
import os.path

from pyramid.httpexceptions import (HTTPBadRequest, HTTPForbidden,
                                    HTTPFound)

from pyramid.response import Response, FileResponse
from pyramid.static import static_view

from pyramid.security import (NO_PERMISSION_REQUIRED,
                              remember, forget,
                              Allow, Everyone)
from pyramid.encode import urlencode

__all__ = ["peter", "peterResourceRoot"]


class peterResourceRoot:
    """
    the login screen is accessible by everyone.
    todo: look up perfect __acl__
    """
    __acl__ = [(Allow, Everyone, 'view'),
               ]

    def __init__(self, request):
        pass


class peter:

    # missing here: the code, which serves the project

    def __init__(self,
                 pyramidConfig,
                 static_assets_peter,
                 static_assets_project,
                 authenticationInterface,
                 minimalPermissions):

        # own root object without any permission
        self.credentialsCheck = authenticationInterface
        self.static_assets_login = static_assets_peter
        self.static_assets_project = static_assets_project
        self.minimalPermissions = minimalPermissions
        peter_config = json.load(open(os.path.join(self.static_assets_login,
                                                   "config.json"),
                                      "r"))
        # setup routes and views
        # these are the API functions, serve them always
        # add own root factory
        pyramidConfig.add_route('peter.api.login',
                                '/api/login',
                                factory=peterResourceRoot)
        pyramidConfig.add_view(self.loginAPIView,
                               route_name="peter.api.login",
                               permission=NO_PERMISSION_REQUIRED)
        pyramidConfig.add_route('peter.api.logout',
                                '/api/logout',
                                factory=peterResourceRoot)
        pyramidConfig.add_view(self.logoutAPIView,
                               route_name="peter.api.logout",
                               permission=NO_PERMISSION_REQUIRED)

        def convenienceLoginForward(request):
            return HTTPFound("/login/")

        # this is a convenience forward
        pyramidConfig.add_route("loginPageRedir",
                                "/login",
                                factory=peterResourceRoot)
        pyramidConfig.add_view(convenienceLoginForward,
                               route_name='loginPageRedir')

        # this serves the login screen
        pyramidConfig.add_route("loginPage",
                                "/login/*subpath",
                                factory=peterResourceRoot)
        pyramidConfig.add_view(static_view(self.static_assets_login,
                                           use_subpath=True,
                                           index="login.html"),
                               route_name='loginPage')

        # generate all resource routes needed from the project folder
        # each string is a URL, which is a file or a directory being served
        # in the static_assets_project directory

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
                pyramidConfig.add_route("peter.projectAsset.%s" %
                                        projectAsset,
                                        "/login/"+projectAsset,
                                        factory=peterResourceRoot)
                pyramidConfig.add_view(projectFileResponse,
                                       route_name=("peter.projectAsset.%s" %
                                                   projectAsset))

            elif os.path.isdir(fileLocation):
                # create a static view
                projectAsset = projectAsset.rstrip("/")
                pyramidConfig.add_route("peter.projectAsset.%s" %
                                        projectAsset,
                                        "/login/"+projectAsset+"/*subpath",
                                        factory=peterResourceRoot)
                pyramidConfig.add_view(static_view(fileLocation,
                                                   use_subpath=True),
                                       route_name=("peter.projectAsset.%s" %
                                                   projectAsset))

    def loginAPIView(self, request):
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
            return HTTPBadRequest(
                        explanation="username or password not supplied",
                        request=request)

        theUser = request.POST["username"]
        # todo: read out password from db
        thePassword = request.POST["password"]

        # make sure there is some user name
        if not self.credentialsCheck(theUser, thePassword):
            logging.debug("login of user '%s' failed" % theUser)
            return HTTPForbidden(explanation="password does not match",
                                 request=request)

        logging.debug("login of user '%s' succeeded" % theUser)
        response_headers = remember(request, theUser)
        response = Response(headers=response_headers)
        return response

    def logoutAPIView(self, request):
        """
        invalidates the session when ``/api/logout`` is called.
        """
        # will logout have some username/email info?
        response_headers = forget(request)
        response = Response(headers=response_headers)
        return response

    def loginPageView(self, request):
        # todo: assure this file is there
        return FileResponse(os.path.join(self.static_assets_login,
                                         "login.html"),
                            request=request)

    def loginPageRedirect(self, request):

        # append direct information
        redirect = request.path
        if redirect in ["", "/"] or redirect.startswith("/login"):
            # don't do a redirect in these cases
            return HTTPFound("/login/")

        if redirect[0] == "/":
            redirect = redirect[1:]

        return HTTPFound("/login/?%s" %
                         urlencode({"redir": request.path}),
                         request=request)
