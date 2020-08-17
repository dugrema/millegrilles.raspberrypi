FROM python:3.8

ENV MG_MQ_SSL=on \
    MG_MQ_AUTH_CERT=on \
    MG_MQ_EXCHANGE_DEFAUT=2.prive

ADD . /opt/src

RUN apt update && \
    apt install -y libboost-python1.67-dev libxml2-dev libxmlsec1-dev i2c-tools \
                   rpi.gpio python3-rpi.gpio python3-smbus python3-cffi python3-setuptools python3-smbus python3-dev && \
    pip3 install rpi.gpio && \
    \
    cd /opt/src/tmp/RF24 && make install && \
    cd pyRF24 && python3 setup.py install && \
    \
    cd /opt/src/tmp/millegrilles.consignation.python && \
    pip3 install -r requirements.txt && \
    python3 setup.py install && \
    \
    cd /opt/src/python && \
    pip3 install -r requirements.txt && \
    python3 setup.py install && \
    \
    cd /opt/src/tmp/arduinolibs/libraries/CryptoLW/python && \
    python3 setup.py install && \
    \
    mkdir -p /opt/millegrilles/etc
