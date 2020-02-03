#!/bin/bash

NB_PARAMS=${#@}
IDMG=$1

source /opt/millegrilles/etc/$IDMG/mg-noeud.conf

python3 mgraspberrypi.py ${@:2:$NB_PARAMS}
