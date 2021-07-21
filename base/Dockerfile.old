FROM docker.maceroc.com/millegrilles_consignation_python_main:1.40.1

USER root

COPY git/ /opt/src/tmp/

RUN export http_proxy=http://fs2.maple.maceroc.com:8000 && \
	\
    pip3 install rpi.gpio smbus && \
    \
    apt update && \
    apt install -y libboost-python1.67 libxml2 libxmlsec1 i2c-tools \
                   rpi.gpio python3-rpi.gpio \
                   python3-smbus python3-cffi python3-setuptools && \
    \
    cd /opt/src/tmp/RF24 && \
    ./configure --driver=RPi && \
    make install && \
    cd pyRF24 && \
    python3 setup.py install && \
    \
    cd /opt/src/tmp/Adafruit_Python_DHT && \
    python3 setup.py install && \
    \
    cd /opt/src/tmp/arduinolibs/libraries/CryptoLW/python && \
    python3 setup.py install && \
    \
    mkdir -p /opt/millegrilles/config && \
    \
    cd / \
    apt remove -y libboost1.67-dev python3-setuptools && \
    rm -rf /var/apt/cache/* /var/lib/apt/lists/* && \
    rm -rf /opt/src
