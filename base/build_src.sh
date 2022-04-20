#!/bin/env bash
set -e

echo "Nom build : $NAME"

GIT_REP=~/git
LIBBOOST=/usr/lib/aarch64-linux-gnu

source image_info.txt

LIBBOOST_DEV_VERSION=libboost-python1.74-dev
LIBBOOST=/usr/lib/aarch64-linux-gnu
# libboost-python1.74.0

sudo pip3 install -r requirements.txt

sudo apt install -y $LIBBOOST_DEV_VERSION \
                    libxml2 libxmlsec1 \
                    rpi.gpio-common python3-rpi.gpio \
                    python3-smbus python3-cffi python3-setuptools
sudo apt install -y i2c-tools

# Ajustement libboost pour python3
sudo ln -sf $LIBBOOST/libboost_python3?.so $LIBBOOST/libboost_python3.so

mkdir -p $GIT_REP

if [ -d $GIT_REP/arduinolibs ]; then
	echo Pull arduinolibs
	git -C $GIT_REP/arduinolibs pull
else
    git -C $GIT_REP/ clone -b python --single-branch https://github.com/dugrema/arduinolibs.git
fi

if [ -d $GIT_REP/RF24 ]; then
	echo Pull RF24
	git -C $GIT_REP/RF24 pull
else
	git -C $GIT_REP/ clone --single-branch https://github.com/nRF24/RF24.git
fi

if [ -d $GIT_REP/Adafruit_Python_DHT ]; then
	echo Pull Adafruit_Python_DHT
    git -C $GIT_REP/Adafruit_Python_DHT pull
else
    git -C $GIT_REP/ clone --single-branch https://github.com/adafruit/Adafruit_Python_DHT.git
fi


# Builds
echo "Build arduinolibs"
cd $GIT_REP/arduinolibs/libraries/CryptoLW/python
sudo python3 setup.py install

echo "Build Adafruit"
cd $GIT_REP/Adafruit_Python_DHT
sudo python3 setup.py install

echo "Build RF24"
cd $GIT_REP/RF24
./configure
echo Makefile original
cat Makefile.inc

# Remplacer flags pour build 64bit:  https://github.com/nRF24/RF24/issues/642
echo "Ajuster makefile pour 64 bit (flags)"
mv Makefile.inc Makefile.inc.old
#true | cat Makefile.inc | grep -v "CPUFLAGS=" | grep -v "CFLAGS=" > Makefile.inc
# cat Makefile.inc | grep -v "CPUFLAGS=" | grep -v "CFLAGS=" > Makefile.inc || true
cat Makefile.inc.old | grep -e "^CPUFLAGS" -e "^CFLAGS" -v > Makefile.inc
echo "CPUFLAGS=" >> Makefile.inc
echo "CFLAGS=-Ofast -Wall -pthread" >> Makefile.inc
cat Makefile.inc

echo "**********\nRF24 pret pour make\n**********"

# Build
make

echo "Installation RF24"
sudo make install

cd pyRF24
python3 setup.py build
sudo python3 setup.py install

echo "Build RF24 termine"
