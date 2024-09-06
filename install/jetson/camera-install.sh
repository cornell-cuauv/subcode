#!/usr/bin/env bash
# download resources for the ZED and Ueye cameras
whoami
export UEYE_SDK=uEyeSDK-4.90.00-ARM_LINUX_IDS_AARCH64_GNU.tgz
export ZED_SDK=ZED_SDK_Tegra_L4T35.4_v4.1.0.zstd.run

# export SPINNAKER_C_SDK=spinnaker-3.2.0.57-arm64-pkg-20.04.tar
# export SPINNAKER_C_FOLDER=spinnaker-3.2.0.57-arm64
# export SPINNAKER_PYTHON_SDK=spinnaker_python-3.2.0.57-cp38-cp38-linux_aarch64.tar
# export SPINNAKER_PYTHON_WHEEL=spinnaker_python-3.2.0.57-cp38-cp38-linux_aarch64

sudo mkdir -p /jetson-camera-tmp
sudo chown -R software /jetson-camera-tmp
pushd /jetson-camera-tmp
if [[ ! -f $UEYE_SDK ]]; then
    sudo -u software curl https://resources.cuauv.org/$UEYE_SDK -O&
fi

if [[ ! -f $UEYE_SDK ]]; then
    sudo -u software curl https://resources.cuauv.org/$ZED_SDK -O && chmod +x $ZED_SDK&
fi

# if [[ ! -f $SPINNAKER_C_SDK ]]; then
#     sudo -u software curl https://resources.cuauv.org/$SPINNAKER_C_SDK -O && tar xvhf $SPINNAKER_C_SDK&
# fi

# if [[ ! -f $SPINNAKER_PYTHON_SDK ]]; then
#     sudo -u software curl https://resources.cuauv.org/$SPINNAKER_PYTHON_SDK -O && tar xvhf $SPINNAKER_PYTHON_SDK&
# fi
# wait

# install ZED sdk
# sorry, because we are running as software, the variable ZED_SDK does not exist
sudo -H -u software bash -c '/jetson-camera-tmp/ZED_SDK_Tegra_L4T32.5_v3.7.7.run --accept --quiet -- --silent'

# install Ueye sdk
pushd /
sudo tar -xvf /jetson-camera-tmp/$UEYE_SDK

# gstreamer dependencies for compressing video in record.py
# only used on sub, that's why they're here
# sudo apt-get -y install gstreamer1.0-tools gstreamer1.1-plugins-base \
#      gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
#      gstreamer1.0-plugins-ugly gstreamer1.0-libav python-gst-1.0
