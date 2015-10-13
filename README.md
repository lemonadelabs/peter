## Build instructions

the commands

```sh
cd git/peter
npm install
npm install bower
./node_modules/bower/bin/bower install
./node_modules/gulp/bin/gulp.js build
```

should produce html/css/js files in `./login`

This project uses the gulp build system which should be installed as well as it's
dependancies by NPM. To serve just the login screen you can just run `gulp` or
`./node_modules/gulp/bin/gulp.js`, which will start servering the app directory
using browser sync.
`gulp build` is will build the project found in `app` into `login`.

`gulp build:serve` will start a browser sync server of the `login` directory so you can check the
build.

The node/gulp/bower components are updated with `npm update` or `bower update`,
which is required occasionally.

## How it works
Peter is a static HTML page with some javascript to drive it. When the user
logs in it will make an AJAX call via jQuery to api/login this call is relative
to the url of the login page. If the server returns a 403 the javascript will
not let the user login and with display an error. If browser cannot find the server
and returns a 404 the javascript will also display and error. If the call and login
is successful and a 200 is returned the javascript will forward the browser to
the `successURL` variable defined in `app/config.json`

For templating we use [Mustache](https://mustache.github.io/) which enables us to
configure the login page with config.json and which then get compiled in when
gulp builds the templates.

## Configuring Peter
The config file for the project and be found in `app/config.json`. This file is
used to pass variables for the templates and for some configuration of the
login behavior.

!!It is important that these changes don't get committed back into the main Peter
project!!

## serve with pyramid

build python3.5 virtual environment with:

* pyramid
* pyramid_debugtoolbar (optional)

run server with calling

```sh
pathToVirtEnv/bin/python login_api/exampleServer.py
```
