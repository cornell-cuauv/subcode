#!/usr/bin/env python3

from build import ninja_common
build = ninja_common.Build('webserver')

# Use "fake" build output to signal to ninja that packages have been installed
build.npm_install('webserver/npm-install.fake', 'webserver/package.json')
build.webpack('static/bundle.js', 'webpack.config.js', 'src', 'webserver/npm-install.fake')

build.install('auv-webserver', f='webserver/auv-webserver.py')
