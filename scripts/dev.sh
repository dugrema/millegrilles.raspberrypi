#!/bin/bash

source /opt/millegrilles/etc/bKKwtXC68HR4TPDzet6zLVq2wPJfc9RiiYLuva/mg-noeud.conf

GITPATH=/home/mathieu/git
PYTHONPATH=$GITPATH/millegrilles.consignation.python:$GITPATH/millegrilles.raspberrypi/python

export PYTHONPATH

python3 ../bin/mgraspberrypi.py --dev --debug --rf24master $1

