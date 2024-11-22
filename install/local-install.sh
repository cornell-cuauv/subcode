# Installation of CPU torch and 

if [[ $(uname -a | grep "tegra") ]]; then
    echo "Skipping OpenCV install on Jetson because it is installed via NV Container"
    exit 0
fi

packages=(
    libopencv-dev
)

apt-get install -y "${packages[@]}"