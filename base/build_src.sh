#!/bin/bash
set -e

source image_info.txt

echo "Nom build : $NAME"

mkdir -p git

if [ -d git/arduinolibs ]; then
	echo Pull arduinolibs
	git -C git/arduinolibs pull
else
    git -C git/ clone -b python --single-branch https://github.com/dugrema/arduinolibs.git
fi

if [ -d git/RF24 ]; then
	echo Pull RF24
	git -C git/RF24 pull
else
	git -C git/ clone --single-branch https://github.com/nRF24/RF24.git
fi

if [ -d git/Adafruit_Python_DHT ]; then
	echo Pull Adafruit_Python_DHT
    git -C git/Adafruit_Python_DHT pull
else
    git -C git/ clone --single-branch https://github.com/adafruit/Adafruit_Python_DHT.git
fi

if [ -d git/Adafruit_Python_BMP ]; then
	echo Pull Adafruit_Python_BMP
    git -C git/Adafruit_Python_BMP pull
else
    git -C git/ clone --single-branch https://github.com/adafruit/Adafruit_Python_BMP.git
fi
