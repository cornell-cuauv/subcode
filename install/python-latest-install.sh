# Install latest version of Python (currently 3.8.0)

# apt-get install -y zlib1g-dev libffi-dev
# apt-get install -y libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev

# mkdir python-latest-install
# cd python-latest-install

# PYTHON_VERSION="3.8.0"
# wget "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"
# tar -xvzf "Python-${PYTHON_VERSION}.tgz"

# cd "Python-${PYTHON_VERSION}"

# ./configure
# make
# make install

# Adding python versions 3.11 and 3.12.
add-apt-repository universe
add-apt-repository ppa:deadsnakes/ppa
# apt-get update
# apt-get install -y python # python2
# apt-get install -y python3.12 python3.12-venv python3.12-dev python3.12-distutils python3.12-lib2to3
# apt-get install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils python3.11-lib2to3
apt-get install -y python3.10 python3.10-venv python3.10-dev python3.10-distutils python3.10-lib2to3

# Install pip for Python 3.8 and upgrade it
# python_versions=("python3.11" "python3.12" "python3") # installing pip
python_versions=("python3.10") # installing pip
for python_version in "${python_versions[@]}"; do
    # $python_version -m ensurepip --upgrade
    $python_version -m pip install --upgrade pip
    $python_version -m pip install numpy==1.26.0
done

echo "Python versions and numpy have been installed successfully."

rm -rf /python-latest-install
