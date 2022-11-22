#!/usr/bin/env bash
set -xeuo pipefail

apt-get install -y libffi-dev openssl libssl-dev libgirepository1.0-dev


if [[ $(uname -a | grep "tegra") ]]; then
    export LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/tegra/
    pip3 install cupy==8.6.0
fi
   
packages=(
    pyserial==3.5
    watchdog==2.1.9

    #cython
    flask==2.2.2
    gevent==22.10.1
    matplotlib==3.6.1
    paramiko==2.11.0
    pyyaml==6.0
    redis==4.3.4
    requests==2.28.1
    six==1.16.0
    tabulate==0.9.0
    termcolor==2.1.0
    tornado==6.2

    eventlet==0.33.1
    posix_ipc==1.0.5

    pygobject==3.42.2

    # pyparsing>=3 conflicts with packaging for some reason
    pyparsing==2.4.7

    nanomsg==1.0

    #numpy
    #scipy

    protobuf==4.21.9

    fire==0.4.0

    tomlkit==0.11.6
    pyratemp==0.3.2
)

# packages2=(
#     posix_ipc
#     # pygame
#     cryptography
# )

packages3=(
    flask==2.2.2
    flask-socketio==5.3.1
    posix_ipc==1.0.5

    pylint==2.15.5
    rope==1.4.0 # Refactoring

    pgi==0.0.11.2
    pycairo==1.21.0

    mypy==0.982
    types-termcolor==1.1.6
    
    # yolov5 requirements
    "torch>=1.7.0"
    "torchvision>=0.8.1"
    "tqdm>=4.64.0"
    "tensorboard>=2.4.1"
    "pandas>=1.1.4"
    "seaborn>=0.11.0"
    ipython
    psutil
    "thop>=0.1.1"
)

# it would be better to not have this
FLAGS="--ignore-installed"

#pip2 install $FLAGS "${packages[@]}" "${packages2[@]}"
pip3 install $FLAGS "${packages[@]}" "${packages3[@]}"
