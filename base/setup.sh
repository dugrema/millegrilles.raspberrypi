#!/bin/bash
set -e

TMP_FOLDER=/opt/src/tmp
GIT_FOLDER=$TMP_FOLDER/git
BASE_FOLDER=$TMP_FOLDER

LIBBOOST_VERSION=libboost-python1.74.0
LIBBOOST_DEV_VERSION=libboost-python1.74-dev
LIBBOOST_PYTHON_DEV_VERSION=libboost-python1.74-dev
LIBBOOST=/usr/lib/aarch64-linux-gnu
# libboost-python1.74.0

pip3 install -r $BASE_FOLDER/requirements.txt

mkdir -p /opt/millegrilles/config

apt update
apt install -y $LIBBOOST_VERSION $LIBBOOST_DEV_VERSION $LIBBOOST_PYTHON_DEV_VERSION \
               libxml2 libxmlsec1 \
               rpi.gpio-common python3-rpi.gpio \
               python3-smbus python3-cffi python3-setuptools
apt install -y i2c-tools

# Ajustement libboost pour python3
ln -sf $LIBBOOST/libboost_python3?.so $LIBBOOST/libboost_python3.so

# Map packages dist
ln -s /usr/lib/python3/dist-packages/RPi /usr/local/lib/python3.9/site-packages/RPi

echo "Installer RF24"
cd $GIT_FOLDER/RF24
./configure
cp Makefile.inc Makefile.inc.old
true || cat Makefile.inc | grep -v "CPUFLAGS=" | grep -v "CFLAGS=" > Makefile.inc
echo "CPUFLAGS=" >> Makefile.inc
echo "CFLAGS=-Ofast -Wall -pthread" >> Makefile.inc
echo Makefile.inc modifie
cat Makefile.inc
make install
echo "Installation module pyRF24"
cd pyRF24
python3 setup.py build
python3 setup.py install

echo "Installer Adafruit Python"
cd $GIT_FOLDER/Adafruit_Python_DHT
python3 setup.py install

echo "Installer crypto Acorn128"
cd $GIT_FOLDER/arduinolibs/libraries/CryptoLW/python
python3 setup.py install

cd /
apt remove -y $LIBBOOST_DEV_VERSION $LIBBOOST_PYTHON_DEV_VERSION
rm -rf /var/apt/cache/* /var/lib/apt/lists/*
#rm -rf /opt/src
