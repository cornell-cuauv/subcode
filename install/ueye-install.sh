
# IDS uEye driver

pushd /tmp
#wget https://cuauv.org/nix-res-private/uEyeSDK-4.90.00-ARM_LINUX_IDS_AARCH64_GNU.tgz
curl https://resources.cuauv.org/uEyeSDK-4.90.00-ARM_LINUX_IDS_AARCH64_GNU.tgz -o /tmp/uEyeSDK-4.90.00-ARM_LINUX_IDS_AARCH64_GNU.tgz


pushd /
tar -xvf /tmp/uEyeSDK-4.90.00-ARM_LINUX_IDS_AARCH64_GNU.tgz
