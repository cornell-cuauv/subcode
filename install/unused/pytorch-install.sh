#!/bin/bash
cd /pytorch-tmp

if [[ -z $(uname -a | grep "tegra") ]]; then
    echo "NOT ON JETSON. INSTALLING CPU VERSION OF PYTORCH"
    # install cpu stuff here
    pip3 install 'torch>=1.8.0'
    pip3 install 'torchvision>=0.9.0'
else    
    # install the Jetson precompiled wheels from loglan
    echo "DETECTED JETSON. INSTALLING PRECOMPILED JETSON WHEELS FOR PYTORCH"
    TORCH=torch-1.8.0-cp38-cp38-linux_aarch64.whl
    TORCH_VISION=torchvision-0.9.0-py38-cp38-linux_aarch64.whl

    if [[ ! -f $TORCH ]]; then
        curl https://resources.cuauv.org/pytorch/$TORCH -O&
    fi

    # Built Version of Torchvision not supported due to bad conversion from .egg to .whl (setup.py did not let a bdist_wheel to be built)
    # if [[ ! -f $TORCH_VISION ]]; then
    #     curl https://resources.cuauv.org/pytorch/$TORCH_VISION -O&
    # fi
    wait

    pip3 install $TORCH

    # grab first line of output to see where torch was installed
    # LIBTORCH_PATH=$( sudo find /usr/local -name "libtorch.so" 2> /dev/null | head -n 1 )
    export LIBTORCH_PATH=/usr/local/cuda/lib64:/home/software/cuauv/workspaces/worktrees/master/link-stage:/usr/lib/aarch64-linux-gnu/tegra/:/home/software/.local/lib/python3.8/site-packages/torch/lib:/usr/local/lib/
    echo LIBTORCH PATH IS: 
    echo $LIBTORCH_PATH
    export PATH=/usr/local/cuda/bin:/home/software/.cargo/bin:/home/software/cuauv/workspaces/worktrees/master/link-stage:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games
    export LD_LIBRARY_PATH=$LIBTORCH_PATH

    # TODO: Set nvcc math and all other LD_LIBRARY_PATHS

    # pip3 install $TORCH_VISION
fi
