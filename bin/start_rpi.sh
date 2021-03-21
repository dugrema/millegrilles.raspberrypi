#!/bin/bash

GIT_PATH=/home/mathieu/git

PYTHON3=/usr/bin/python3
export PYTHONPATH=$GIT_PATH/millegrilles.consignation.python:$GIT_PATH/millegrilles.raspberrypi/python

export MG_NOEUD_ID="c31dc850-ff18-4a82-b15b-abf8b0acef2b"
export MG_IDMG="z2W2ECnP9eauNXD628aaiURj6tJfSYiygTaffC1bTbCNHCtomhoR7s"
export RF24_PA=0

CERTS=/home/mathieu/mgdev/certs
export MG_MQ_HOST=mg-dev4.maple.maceroc.com
export MG_MQ_PORT=5673
export MG_MQ_CA_CERTS=$CERTS/pki.millegrille.cert
export MG_MQ_KEYFILE=$CERTS/pki.monitor.key
export MG_MQ_CERTFILE=$CERTS/pki.monitor.cert
export MG_MQ_SSL=on
export MG_MQ_AUTH_CERT=on
export MG_MQ_EXCHANGE_DEFAUT="2.prive"

# python3 -m mgraspberry.raspberrypi.Demarreur --debug --noconnect --dummysenseurs nofork
# python3 -m mgraspberry.raspberrypi.Demarreur --debug --dev --rf24master nofork
python3 -m mgraspberry.raspberrypi.Demarreur --debug --dev --dummysenseurs --lcdsenseurs nofork
# python3 -m mgraspberry.raspberrypi.Demarreur --debug --dev --lcdsenseurs --rf24master --am2302 18 nofork
# python3 -m mgraspberry.raspberrypi.Demarreur --debug --dev --am2302 18 nofork
# python3 -m mgraspberry.raspberrypi.Demarreur --debug --noconnect --dev --rf24master nofork


