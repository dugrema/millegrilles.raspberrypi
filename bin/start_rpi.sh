#!/bin/bash

GIT_PATH=/home/mathieu/git

PYTHON3=/usr/bin/python3
export PYTHONPATH=$GIT_PATH/millegrilles.consignation.python:$GIT_PATH/millegrilles.raspberrypi/python

export MG_NOEUD_ID="de85cd60-39d6-454e-b903-e5381f0634e7"
export MG_IDMG="QME8SjhaCFySD9qBt1AikQ1U7WxieJY2xDg2JCMczJST"
export RF24_PA=3

CERTS=/home/mathieu/mgdev/certs
export MG_MQ_PORT=5673
export MG_MQ_CA_CERTS=$CERTS/pki.millegrille.cert
export MG_MQ_KEYFILE=$CERTS/pki.monitor.key.20201028191224
export MG_MQ_CERTFILE=$CERTS/pki.monitor.cert.20201028191224
export MG_MQ_SSL=on
export MG_MQ_AUTH_CERT=on
export MG_MQ_EXCHANGE_DEFAUT="2.prive"

# python3 -m mgraspberry.raspberrypi.Demarreur --debug --noconnect --dummysenseurs nofork
# python3 -m mgraspberry.raspberrypi.Demarreur --debug --dev --rf24master nofork
# python3 -m mgraspberry.raspberrypi.Demarreur --debug --dev --lcdsenseurs nofork
# python3 -m mgraspberry.raspberrypi.Demarreur --debug --dev --lcdsenseurs --rf24master --am2302 18 nofork
# python3 -m mgraspberry.raspberrypi.Demarreur --debug --dev --am2302 18 nofork
python3 -m mgraspberry.raspberrypi.Demarreur --debug --noconnect --dev --rf24master nofork


