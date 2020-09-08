FROM docker.maceroc.com/millegrilles_consignation_python_main:1.31.21

ENV MG_CONFIG=/opt/millegrilles/config \
    MG_MQ_SSL=on \
    MG_MQ_AUTH_CERT=on \
    MG_MQ_EXCHANGE_DEFAUT=2.prive

VOLUME /opt/millegrilles/config

ADD . /opt/src

USER root

RUN mkdir -p /opt/src/tmp && \
    git -C /opt/src/tmp clone -b python --single-branch https://github.com/dugrema/arduinolibs.git && \
    git -C /opt/src/tmp clone --single-branch https://github.com/nRF24/RF24.git && \
    \
    apt update && \
    apt install -y libboost-python1.67 libxml2 libxmlsec1 i2c-tools \
                   rpi.gpio python3-rpi.gpio python3-smbus python3-cffi \
                   python3-setuptools python3-smbus && \
    pip3 install rpi.gpio && \
    \
    cd /opt/src/tmp/RF24 && \
    ./configure --driver=RPi && \
    make install && \
    cd pyRF24 && \
    python3 setup.py install && \
    \
    cd /opt/src/python && \
    pip3 install -r requirements.txt && \
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
