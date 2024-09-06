packages=(
  python3.11
  python3-pip
  libblas-dev
  liblapack-dev
  libatlas-base-dev
  gfortran
  zlib1g-dev
  libffi-dev
  libreadline-gplv2-dev
  libncursesw5-dev
  libssl-dev
  libsqlite3-dev
  tk-dev
  libgdbm-dev
  libc6-dev
  libbz2-dev
)

for f in ${packages[@]}; do
  apt install -y --no-install-recommends $f
done

mkdir python-latest-install
cd python-latest-install

PYTHON_VERSION="3.12.0"
wget "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"
tar -xvzf "Python-${PYTHON_VERSION}.tgz"

cd "Python-${PYTHON_VERSION}"

./configure
make
make install

rm -rf /python-latest-install

cd /
pip3 install --cache-dir $PIP_CACHE_DIR --upgrade pip
pip3 install scipy Cython

