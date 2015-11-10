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
'''

import base64
import random
import datetime
import logging
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

    """
    This project needs a bunch of call-backs.

    If the callbacks are not provided, some features can not be delivered.
    """

    def __init__(self,
                 pyramidConfig,
                 static_assets_peter,
                 static_assets_project,
                 checkUserPassword,
                 checkUserEmail=None,
                 sendPasswordResetEmail=None,
                 setNewPasswordHash=None,
                 storeRequestToken=None,
                 retreiveRequestToken=None,
                 deleteRequestToken=None,
                 projectMinPermissions="view"):

        """
        :param: pyramidConfig is the configuration to which the routes and
           views are added.

        :param: checkUserPassword is a callback, taking username and
           password and returning None if authentication fails or the username
           as it should be remembered.

        :param: sendResetMail callback taking username, email and
           reset page URL. Provision and further customization of a template is
           left to the callback.

        :param: checkUserEmail for password reset: if username and email
            address do not match, no reminder email is sent.

        :param: setNewPasswordHash takes username and new password hash.

        :param: storeRequestToken a persistent storage for the auth tokens.
           this callback takes: token, username, requestType, expiryDate

        :param: retreiveRequestToken

        :param: deleteRequestToken
        """

        # own root object without any permission
        self.credentialsCheck = checkUserPassword
        self.static_assets_login = static_assets_peter
        self.static_assets_project = static_assets_project
        self.minPermissions = projectMinPermissions
        # setup routes and views
        # these are the API functions, serve them always
        # add own root factory

        self.checkUserEmail = checkUserEmail
        self.sendPasswordResetEmail = sendPasswordResetEmail
        self.setNewPasswordHash = setNewPasswordHash
        self.storeRequestToken = storeRequestToken
        self.retreiveRequestToken = retreiveRequestToken
        self.deleteRequestToken = deleteRequestToken

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

        self.projectView = static_view(root_dir=self.static_assets_project,
                                       use_subpath=True)

    def resetRequestView(self, context, request):
        """
        expect username and email, generate and store token, send it by email
        this token will be used with the new password to resetAction

        maybe emailaddress to verify account (a little bit)
        """

        if "username" not in request.params:
            return HTTPBadRequest("no username supplied")
        if "email" not in request.params:
            return HTTPBadRequest("no email supplied")

        username = request.params["username"]
        email = request.params["email"]

        if username == "" or email == "":
            return HTTPBadRequest("username or email not supplied")

        # check whether email supplied is the same?!
        if not self.checkUserEmail(username, email):
            return Response()
        logging.debug("password reset request for %s and %s" % (username,
                                                                email))

        token = self.tokenGenerator()

        expiryDate = datetime.datetime.now()+datetime.timedelta(24*3600)
        self.storeRequestToken(token, "resetPwd", username, expiryDate)

        tokenURL = request.route_url("peter.loginPage",
                                     subpath="resetpassword.html",
                                     _query=({"token": token}))

        self.sendPasswordResetEmail(username, email, tokenURL)
        response = Response()
        return response

    def tokenGenerator(self):
        tokenLength = 24  # should be a multiple of 4

        token = base64.urlsafe_b64encode(bytes([random.randrange(0, 256)
                                                for _ in range(
                                                    int(tokenLength/4*3))]
                                               )
                                         ).decode('utf-8')
        return token

    def resetPasswordView(self, context, request):

        if not ("token" in request.params and
                "newPasswordHash" in request.params):
            return HTTPBadRequest("'token' or 'newPasswordHash'"
                                  " parameters missing")

        token = request.params["token"]
        pwdHash = request.params["newPasswordHash"]

        tokenInfo = self.retreiveRequestToken(token)
        if tokenInfo is None:
            # do not say much!
            return HTTPForbidden("invalid token")

        purpose, username, expiryDate = tokenInfo
        if purpose != "resetPwd":
            # unknown token, do not say much!
            return HTTPForbidden("invalid token")

        if expiryDate < datetime.datetime.now():
            # expired token, do not say much!
            self.deleteRequestToken(token)
            return HTTPForbidden("invalid token")

        # todo: any password policy?
        # todo: check return value
        self.setNewPasswordHash(username, pwdHash)

        self.deleteRequestToken(token)
        return Response()

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
