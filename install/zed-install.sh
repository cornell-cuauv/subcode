cd /usr/local/zed
yes | python3 get_python_api.py
#yes | python3 -m pip uninstall numpy
#pip install -y numpy==1.26.4

# This script will setup USB rules to open the ZED cameras without root access
# This can also be useful to access the cameras from a docker container without root (this script needs to be run on the host)
# NB: Running the ZED SDK installer will already setup those

# Print the commands
set -x
# Download the lightest installer
wget -q https://download.stereolabs.com/zedsdk/4.1/l4t36.3/jetsons -O zed_installer.run

# Extracting only the file we're interested in
bash ./zed_installer.run --tar -x './99-slabs.rules'  > /dev/null 2>&1
mv "./99-slabs.rules" "/etc/udev/rules.d/"
chmod 777 "/etc/udev/rules.d/99-slabs.rules"
udevadm control --reload-rules && sudo udevadm trigger

# Utilized for the ZED Diagnostic, if needed
apt-get update
apt-get install -y libqt5sql5 libqt5xml5 qtbase5-dev
