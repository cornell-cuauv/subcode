# Install Python 3.7

mkdir python3.7-install
cd python3.7-install

PYTHON_VERSION="3.7.3"
wget "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"
tar -xvzf "Python-${PYTHON_VERSION}.tgz"

./configure
make
make altinstall
