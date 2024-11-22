#!/usr/bin/env bash
python3 -m pip install --upgrade pip
set -xeuo pipefail

dependencies=(
    Cython==3.0.11
    eventlet==0.33.1
    fire==0.4.0
    gevent==22.10.1
    jinja2==3.1.4
    matplotlib==3.6.1
    nanomsg==1.0
    numpy==1.26.4       # keep as 1.26.4. Any newer, zed breaks. Any older, scipy breaks
    pyparsing==2.4.7    # pyparsing>=3 conflicts with packaging for some reason
    pyratemp==0.3.2
    pyyaml==6.0
    pyzmq==26.2.0
    redis==4.3.4
    scipy==1.10.0
    six==1.16.0
    tabulate==0.9.0
    termcolor==2.1.0
    tomlkit==0.11.6
    tornado==6.2
    watchdog==2.1.9
)

jetson_dependencies=(
    cupy-cuda12x
)

local_dependencies=(
    gql
    aiohttp
) 

ultralytics_dependencies=(
    certifi                     # use the latest
    dill==0.3.9
    idna==3.10
    pandas==2.2.3
    pillow==10.2.0
    psutil==6.1.0
    py-cpuinfo==9.0.0
    seaborn==0.13.2
    tqdm==4.67.0
    ultralytics-thop==2.0.11
    urllib3==2.2.3
    requests==2.32.3
    chardet==5.2.0
    ultralytics==8.3.29
)

# it would be better to not have this
# pip3 likes to reinstall already existing dependencies

pip3 install "${dependencies[@]}"
if [[ $(uname -a | grep "tegra") ]]; then
    export LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/tegra/
    if [[ "${jetson_dependencies[@]}" != "" ]]; then
        pip3 install "${jetson_dependencies[@]}"
    fi
else
    if [[ "${local_dependencies[@]}" != "" ]]; then
        pip3 install "${local_dependencies[@]}"
    fi
    pip3 install torch --ignore-installed --index-url https://download.pytorch.org/whl/cpu
    pip3 install torchvision --ignore-installed --index-url https://download.pytorch.org/whl/cpu
fi

pip3 install --no-deps "${ultralytics_dependencies[@]}"
