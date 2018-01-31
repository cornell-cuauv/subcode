#!/usr/bin/env bash
set -xeuo pipefail

packages=(
    pyserial
    watchdog

    cython
    flask
    gevent
    matplotlib
    paramiko
    pyyaml
    redis
    requests
    scipy
    six
    tabulate
    termcolor
    tornado

    eventlet
    posix_ipc

    pygobject

    nanomsg
    pylint
)

packages2=(
    posix_ipc
    pygame
)

packages3=(
    flask
    flask-socketio
    posix_ipc
)

pip2 install "${packages[@]}" "${packages2[@]}"
pip3 install "${packages[@]}" "${packages3[@]}"
