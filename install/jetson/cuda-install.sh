#!/usr/bin/env bash

### dependency install 
pushd /jetson-tmp
packages=(
    bzip2
    unp
    sudo
    pigz
    lbzip2
    libasound2
    qemu-user-static
    libegl1-mesa
    libgstreamer-plugins-bad1.0
    libunwind8
    device-tree-compiler
)

apt-get install -y "${packages[@]}"
cp /usr/bin/qemu-aarch64-static .
wget -qO - http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1404/x86_64/7fa2af80.pub | sudo apt-key add -

# These links come from the repository.json file downloaded by JetPack
# NOTE FOR THE FUTURE: NVIDIA has put the downloads behind a login, so we're 
# just gonna manually download them and upload them to loglan.

JETPACK_VERSION="Jetson_Linux_R32.5.2_aarch64_1.tbz2"
NV_DEB_FILENAMES=(
    "T186/$JETPACK_VERSION"
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

tar --use-compress-prog=bzip2 -xpf $JETPACK_VERSION 

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

#install downloaded files
for NV_DEB_FILENAME in "${NV_DEB_FILENAMES[@]}"; do
    if [[ ${NV_DEB_FILENAME#REMOVE_PREFIX} == *.tbz2 ]]; then
        # prevent the installer from trying to overwrite /etc/hostname and /etc/hosts
        # this is (obviously) super jank
        sed -i '/tar -I lbzip2 -xpmf \${LDK_NV_TEGRA_DIR}\/config.tbz2/ s/$/ --exclude='\''etc\/host*'\''/' Linux_for_Tegra/apply_binaries.sh

        ./Linux_for_Tegra/apply_binaries.sh -r /
        rm -rf ./LINUX_for_Tegra
    elif [[ $NV_DEB_FILENAME == *.deb ]]; then
        dpkg -i "./$(basename $NV_DEB_FILENAME)"
    else
        echo "Unhandled file type of ${NV_DEB_FILENAME}"
        exit 1
    fi
done

mknod -m 444 "/dev/random" c 1 8
mknod -m 444 "/dev/urandom" c 1 9
sed -i'' 's/<SOC>/t186/g' /etc/apt/sources.list.d/nvidia-l4t-apt-source.list

apt-get update -o Acquire::CompressionTypes::Order::=gz -y
apt-get install -y --allow-unauthenticated cuda-toolkit-10.2

export LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}:/usr/lib/aarch64-linux-gnu/tegra

ln -s /usr/lib/aarch64-linux-gnu/libcuda.so /usr/lib/aarch64-linux-gnu/libcuda.so.1
ln -s /usr/lib/aarch64-linux-gnu/tegra/libnvidia-ptxjitcompiler.so.440.18 /usr/lib/aarch64-linux-gnu/tegra/libnvidia-ptxjitcompiler.so
ln -s /usr/lib/aarch64-linux-gnu/tegra/libnvidia-ptxjitcompiler.so.440.18 /usr/lib/aarch64-linux-gnu/tegra/libnvidia-ptxjitcompiler.so.1
