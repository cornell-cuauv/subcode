#!/usr/bin/env bash

### dependency install 
pushd /jetson-tmp
packages=(
    bzip2
    unp
    sudo
    pigz
    lbzip2
    qemu-user-static
    libegl1-mesa
    libgstreamer-plugins-bad1.0
    libunwind8
    device-tree-compiler
)

apt-get install -y "${packages[@]}"
wget -qO - http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1404/x86_64/7fa2af80.pub | sudo apt-key add -

# These links come from the repository.json file downloaded by JetPack
# NOTE FOR THE FUTURE: NVIDIA has put the downloads behind a login, so we're 
# just gonna manually download them and upload them to loglan.

NV_DEB_FILENAMES=(
    "T186/Jetson_Linux_R32.5.1_aarch64_1.tbz2"
    "T186/Jetson_Linux_R32.5.2_aarch64_1.tbz2"
    "cuda-repo-l4t-10-2-local-10.2.89_1.0-1_arm64.deb"
    "libcudnn8_8.0.0.180-1+cuda10.2_arm64.deb"
    "libcudnn8-dev_8.0.0.180-1+cuda10.2_arm64.deb"
    "libcudnn8-doc_8.0.0.180-1+cuda10.2_arm64.deb"
)

# download
REMOVE_PREFIX="T186/"
for NV_DEB_FILENAME in "${NV_DEB_FILENAMES[@]}"; do
    if [[ ! -f ${NV_DEB_FILENAME#$REMOVE_PREFIX} ]]; then
        curl "https://resources.cuauv.org/${NV_DEB_FILENAME}" -O&
    fi
done
wait

tar --use-compress-prog=bzip2 -xpf "Jetson_Linux_R32.5.2_aarch64_1.tbz2"

# Python 2.7 is somehow required to install one of the packages below
# don't change the order or else dkpg -i will scream
PYTHON_FILENAMES=(
    "libpython2.7-minimal_2.7.15~rc1-1_arm64.deb"
    "libpython2.7-stdlib_2.7.15~rc1-1_arm64.deb"
    "libpython-stdlib_2.7.15~rc1-1_arm64.deb"
    "libpython2.7_2.7.15~rc1-1_arm64.deb"
    "python2.7-minimal_2.7.15~rc1-1_arm64.deb"
    "python2.7_2.7.15~rc1-1_arm64.deb"
    "python-minimal_2.7.15~rc1-1_arm64.deb"
    "python_2.7.15~rc1-1_arm64.deb"
)

for PYTHON_FILENAME in "${PYTHON_FILENAMES[@]}"; do
    if [[ ! -f $PYTHON_FILENAME ]]; then
        wget "https://launchpad.net/ubuntu/+archive/primary/+files/$PYTHON_FILENAME"
    fi
    dpkg -i $PYTHON_FILENAME
done
