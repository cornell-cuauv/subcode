#!/bin/bash
cd /pytorch-tmp

if [[ -z $(uname -a | grep "tegra") ]]; then
    echo "NOT ON JETSON. INSTALLING CPU VERSION OF PYTORCH"
    # install cpu stuff here
    pip3 install 'torch>=1.8.0'
    pip3 install 'torchvision>=0.9.0'
else
    # Install torchvision from source since wheel does not work
    sudo apt-get install -y libjpeg-dev zlib1g-dev libpython3-dev libopenblas-dev libavcodec-dev libavformat-dev libswscale-dev
    echo INSTALLING TORCHVISION FROM SOURCE
    if [[ ! -d "torchvision" ]]; then
        git clone --branch v0.9.0 https://github.com/pytorch/vision torchvision   # see below for version of torchvision to download
    fi

    chown -R software torchvision/
    cd torchvision
    # where 0.x.0 is the torchvision version
    sudo -H -u software bash -c 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:/home/software/cuauv/workspaces/worktrees/master/link-stage:/usr/lib/aarch64-linux-gnu/tegra/:/home/software/.local/lib/python3.8/site-packages/torch/lib:/usr/local/lib/'
    sudo -H -u software bash -c 'export PATH=/usr/local/cuda/bin:/home/software/.cargo/bin:/home/software/cuauv/workspaces/worktrees/master/link-stage:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games'
    
    sudo -u software export LD_LIBRARY_PATH=/usr/local/cuda/lib64:/home/software/cuauv/workspaces/worktrees/master/link-stage:/usr/lib/aarch64-linux-gnu/tegra/:/home/software/.local/lib/python3.8/site-packages/torch/lib:/usr/local/lib/
    sudo -u software export PATH=/usr/local/cuda/bin:/home/software/.cargo/bin:/home/software/cuauv/workspaces/worktrees/master/link-stage:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games

    export PATH=/usr/local/cuda/bin:/home/software/.cargo/bin:/home/software/cuauv/workspaces/worktrees/master/link-stage:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games
    export LIBTORCH_PATH=/usr/local/cuda/lib64:/home/software/cuauv/workspaces/worktrees/master/link-stage:/usr/lib/aarch64-linux-gnu/tegra/:/home/software/.local/lib/python3.8/site-packages/torch/lib:/usr/local/lib/
    
    echo AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    sudo -u software echo $LD_LIBRARY_PATH
    sudo -u software echo $PATH

    sudo -u software export BUILD_VERSION=0.9.0
    sudo -u software python3.8 setup.py install --user
    
    # sudo -H -u software bash -c 'whoami && export BUILD_VERSION=0.9.0 && python3.8 setup.py install --user'
    cd ../  # attempting to load torchvision from build dir will result in import error
fi