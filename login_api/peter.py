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
import datetime
import logging
import json
import os.path

from pyramid.httpexceptions import (HTTPBadRequest, HTTPForbidden,
                                    HTTPFound, HTTPNotFound,
                                    HTTPInternalServerError)

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
                 projectMinPermissions="view"):

        """
        :param: pyramidConfig is the configuration to which the routes and
           views are added.

        :param: authenticationInterface is a callable, taking user and password
           and returning None if authentication fails or the username as it
           should be remembered.
        """

        # own root object without any permission
        self.credentialsCheck = authenticationInterface
        self.static_assets_login = static_assets_peter
        self.static_assets_project = static_assets_project
        self.minPermissions = projectMinPermissions
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

        pyramidConfig.add_route("peter.api.resetRequest",
                                "/api/resetrequest",
                                factory=peterResourceRoot)
        pyramidConfig.add_view(self.resetRequestView,
                               route_name="peter.api.resetRequest",
                               permission=NO_PERMISSION_REQUIRED)

        pyramidConfig.add_route("peter.api.resetPassword",
                                "/api/resetpassword",
                                factory=peterResourceRoot)
        pyramidConfig.add_view(self.resetPasswordView,
                               route_name="peter.api.resetPassword",
                               permission=NO_PERMISSION_REQUIRED)

        def convenienceLoginForward(request):
            return HTTPFound("/login/")

        # this is a convenience forward
        pyramidConfig.add_route("peter.loginPageRedir",
                                "/login",
                                factory=peterResourceRoot)
        pyramidConfig.add_view(convenienceLoginForward,
                               route_name='peter.loginPageRedir')

        # this serves the login screen
        pyramidConfig.add_route("peter.loginPage",
                                "/login/*subpath",
                                factory=peterResourceRoot)
        pyramidConfig.add_view(static_view(self.static_assets_login,
                                           use_subpath=True,
                                           index="login.html"),
                               route_name='peter.loginPage')

        # generate all resource routes needed from the project folder
        # each string is a URL, which is a file or a directory being served
        # in the static_assets_project directory

        peter_config_file = os.path.join(static_assets_peter, "config.json")
        peter_config = json.load(open(peter_config_file, "r"))
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

        self.projectView = static_view(root_dir=self.static_assets_project,
                                       use_subpath=True)

    def resetRequestView(self, context, request):
        """
        expect username, generate and store token, send it by email
        this token will be used with the new password to resetAction

        maybe emailaddress to verify account (a little bit)
        """
        logging.debug("reset request")
        if "username" not in request.params:
            return HTTPBadRequest("no username supplied")

        username = request.params["username"]

        # get email address
        email = self.getEmailAddress(username)
        if email is None:
            return HTTPNotFound("user not found or has no email address")

        # todo: check whether email supplied is the same?!

        token = self.tokenGenerator()

        expiryDate = datetime.datetime.now()+datetime.timedelta(24*3600)
        self.storeToken(token, "resetPwd", username, expiryDate)

        tokenURL = request.route_url("peter.loginPage",
                                     subpath="resetPassword.html",
                                     _query=({"username": username,
                                              "token": token}))

        self.sendPasswordResetEmail(username, email, tokenURL)
        response = Response()
        return response

    def resetPasswordView(self, context, request):

        if not ("token" in request.params and
                "newPasswordHash" in request.params):
            return HTTPBadRequest("'token' or 'newPasswordHash'"
                                  " parameters missing")

        token = request.params["token"]
        pwdHash = request.params["newPasswordHash"]

        tokenInfo = self.retreiveToken(token)
        if tokenInfo is None:
            # do not say much!
            return HTTPForbidden("invalid token")

        purpose, username, expiryDate = tokenInfo
        if purpose != "resetPwd":
            # do not say much!
            return HTTPForbidden("invalid token")

        if expiryDate < datetime.datetime.now():
            # do not say much!
            self.invalidateToken(token)
            return HTTPForbidden("invalid token")

        # todo: any password policy?
        # todo: check return value
        self.resetPassword(username, pwdHash)

        self.invalidateToken(token)
        return Response()

    def getEmailAddress(self, username):
        if username == "achim":
            return "achim.gaedke@lemonadelabs.io"

        return None

    def resetPassword(self, username, pwdHash):
        logging.info("resetting password for user %s" % username)

    def tokenGenerator(self):
        tokenLength = 24  # should be a multiple of 4

        token = base64.urlsafe_b64encode(bytes([random.randrange(0, 256)
                                                for _ in range(
                                                    int(tokenLength/4*3))]
                                               )
                                         ).decode('utf-8')
        return token

    def storeToken(self, token, purpose, username, expiryDate):
        if not hasattr(self, "tokenStorage"):
            self.tokenStorage = {}

        self.tokenStorage[token] = (purpose, username, expiryDate)

    def retreiveToken(self, token):
        if not hasattr(self, "tokenStorage"):
            return None

        return self.tokenStorage.get(token, None)

    def invalidateToken(self, token):
        if not hasattr(self, "tokenStorage"):
            return None

        if token in self.tokenStorage:
            del self.tokenStorage[token]

    def sendPasswordResetEmail(self, username, email, tokenURL):

        # find out first and last name

        subject = "Password Reset for Simone"
        text = "Hello %s!\n%s" % (username, tokenURL)

        api_key = ""  # todo: readout from config file!
        email = "Achim.Gaedke@lemonadelabs.io"
        fullname = "Achim Gaedke"

        # https://mandrillapp.com/api/docs/messages.python.html#method=send
        import mandrill
        try:
            mandrill_client = mandrill.Mandrill(api_key)
            message = {'auto_html': True,
                       'from_email': 'simone@lemonadelabs.io',
                       'from_name': 'simone@lemonadelabs.io',
                       'headers': {'Reply-To': 'support@lemonadelabs.io'},
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
        except mandrill.Error as e:
            # Mandrill errors are thrown as exceptions
            logging.error('A mandrill error occurred: %s - %s' %
                          (e.__class__, e))

            raise HTTPInternalServerError
        finally:
            del result

    def staticAssetsProjectView(self, context, request):
        if not request.has_permission(self.minPermissions,
                                      context=context):
            return self.loginPageRedirect(request)

        return self.projectView(context, request)

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

        checkedUser = self.credentialsCheck(theUser, thePassword)

        # make sure there is some user name
        if checkedUser is None:
            logging.debug("login of user '%s' failed" % theUser)
            return HTTPForbidden(explanation="password does not match",
                                 request=request)

        logging.debug("login of user '%s' succeeded" % theUser)
        response_headers = remember(request, checkedUser)
        response = Response(headers=response_headers)
        return response

    def logoutAPIView(self, request):
        """
        invalidates the session when ``/api/logout`` is called.
        """
        logging.debug("logout")
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
