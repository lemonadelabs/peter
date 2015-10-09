## Build instructions

the commands

```sh
cd git/peter
npm install
npm install bower
./node_modules/bower/bin/bower install
./node_modules/gulp/bin/gulp.js build
```

should produce html/css/js files in `./build`

When the project is updated a `gulp build` is will rebuild the contents of `build`.

The node/gulp/bower components are updated with `npm update` or `bower update`,
which is required occasionally.

## serve with pyramid

build python3.5 virtual environment with:

* pyramid
* pyramid_debugtoolbar (optional)

run server with calling

```sh
pathToVirtEnv/bin/python login_api/exampleServer.py
```

