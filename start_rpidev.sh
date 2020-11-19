#!/bin/bash

export PYTHONPATH=/home/mathieu/git/millegrilles.consignation.python/:/home/mathieu/git/millegrilles.raspberrypi/python

CERT_FOLDER=/home/mathieu/mgdev/certs
DATE_CERT=20201119152929

export MG_MQ_CA_CERTS=$CERT_FOLDER/pki.millegrille.cert
export MG_MQ_KEYFILE=$CERT_FOLDER/pki.monitor.key.$DATE_CERT
export MG_MQ_CERTFILE=$CERT_FOLDER/pki.monitor.cert.$DATE_CERT
export MG_MQ_HOST=climatdubrasseur2.maple.maceroc.com
export MG_MQ_PORT=5673
export MG_MQ_SSL=on
export MG_MQ_AUTH_CERT=on
export "MG_MQ_EXCHANGE_DEFAUT=2.prive"
export MG_NOEUD_ID=9c67c2c0-583a-4a52-af9b-465e3a48aed0

python3 -m mgraspberry.raspberrypi.Demarreur --debug --bmp180 nofork
# python3 -m mgraspberry.raspberrypi.Demarreur --debug --dummysenseurs --rf24master nofork
# python3 -m mgraspberry.raspberrypi.Demarreur --dev --debug --dummy nofork
