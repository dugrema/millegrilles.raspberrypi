#!/bin/bash

GITPATH=/home/mathieu/git
PYTHONPATH=$GITPATH/millegrilles.consignation.python:$GITPATH//millegrilles.raspberrypi/python

export PYTHONPATH

python3 ./mgraspberrypi.py --rf24master --idmg abcd $1

