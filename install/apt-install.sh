#!/usr/bin/env bash

packages=(
    # general
    autossh
    bc
    dialog
    gnuplot
    htop
    iotop
    iputils-ping
    iputils-tracepath
    jq
    
    #libboost-python-dev
    libeigen3-dev
    libgtest-dev
    libncurses-dev
    libpopt-dev
    libpython3-dev
    nano
    llvm-dev
    libclang-dev
    clang
    neovim
    nload
    rsync
    screen
    shellcheck
    silversearcher-ag
    stow
    tmux
    usbutils
    wget
    vlc
    dnsutils
    gdb
    valgrind

    # serial
    libgtest-dev
    libgtkmm-3.0-dev
    libprotobuf-dev
    libprotoc-dev
    protobuf-compiler

    # vision
    libavcodec-dev
    libavformat-dev
    libdc1394-dev
    libswscale-dev
    libturbojpeg

    # trogdor
    expect-dev

    # visualizer
    libconfig++
    libglfw3-dev
    libglm-dev

    # fishbowl
    libeigen3-dev

    # auvlog
    libnanomsg-dev
    redis-server

    # syscheck
    sysstat

    # aslam
    liblzma-dev

    #slam
    libzmq3-dev

    # Migrated from pip-install
    libffi-dev
    openssl
    libssl-dev
    libgirepository1.0-dev

    # Migrated from python-latest-pip-install
    libblas-dev
    liblapack-dev
    libatlas-base-dev
    gfortran
)

apt-get install -y software-properties-common # For add-apt-repository
apt-get install -y libdbus-1-dev
add-apt-repository ppa:neovim-ppa/stable
apt-get clean -y
apt-get update -o Acquire::CompressionTypes::Order::=gz -y

apt-get install -y "${packages[@]}" ||
    apt-get install -y "${packages[@]}" ||
    apt-get install -y "${packages[@]}"

# Add Neovim alternatives (https://github.com/neovim/neovim/wiki/Installing-Neovim)
update-alternatives --install /usr/bin/vi vi /usr/bin/nvim 60
update-alternatives --config vi
update-alternatives --install /usr/bin/vim vim /usr/bin/nvim 60
update-alternatives --config vim
update-alternatives --install /usr/bin/editor editor /usr/bin/nvim 60
update-alternatives --config editor


# ***************** gtest *******************
cd /usr/src/gtest
cmake CMakeLists.txt
make

# copy or symlink libgtest.a and libgtest_main.a to your /usr/lib folder
cd lib/
cp *.a /usr/lib
