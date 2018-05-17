#!/usr/bin/env bash
set -xeuo pipefail

apt-get install -y libffi-dev openssl libssl-dev

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

    cupy
)

packages2=(
    posix_ipc
    pygame
    cryptography
)

packages3=(
    flask
    flask-socketio
    posix_ipc

    pylint
    rope # Refactoring
)

pip2 install "${packages[@]}" "${packages2[@]}"
pip3 install "${packages[@]}" "${packages3[@]}"
