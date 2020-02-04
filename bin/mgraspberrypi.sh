#!/bin/bash

NB_PARAMS=${#@}
IDMG=$1

source /var/opt/millegrilles/$IDMG/etc/mg-noeud.conf

python3 /opt/millegrilles/bin/mgraspberrypi.py ${@:2:$NB_PARAMS}
