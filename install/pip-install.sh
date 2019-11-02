#!/usr/bin/env bash
set -xeuo pipefail

apt-get install -y libffi-dev openssl libssl-dev libgirepository1.0-dev

if [[ "$(uname -m)" = "aarch64" ]]; then
    export LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/tegra/
    pip2 install cupy
    pip3 install cupy
fi

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
    six
    tabulate
    termcolor
    tornado

    eventlet
    posix_ipc

    pygobject

    nanomsg

    numpy
    scipy

    protobuf

    fire

    tomlkit
)

packages2=(
    posix_ipc
    # pygame
    cryptography
)

packages3=(
    flask
    flask-socketio
    posix_ipc

    pylint
    rope # Refactoring

    pgi
    pycairo
)

packages_latest=(
    mypy
)

# it would be better to not have this
FLAGS=--force-reinstall greenlet

pip2 install "${packages[@]}" "${packages2[@]}" $FLAGS
pip3 install "${packages[@]}" "${packages3[@]}" $FLAGS
pip3.8 install "${packages[@]}" "${packages3[@]}" "${packages_latest[@]}" $FLAGS
