#!/bin/bash

FICHIER_CONFIG=../etc/mg-appareils.conf
#FICHIER_CONFIG=/usr/local/etc/millegrilles/mg-appareils.conf
SCRIPT_PYTHON=/home/mathieu/git/MilleGrilles.raspberrypi/scripts/mgraspberrypi.py
COMMAND=$1

if [ ! -f $FICHIER_CONFIG ]; then
  echo "Le fichier de configuration est introuvable: $FICHIER_CONFIG"
  exit 1
fi

source $FICHIER_CONFIG

#export MG_NOM_MILLEGRILLE=maple
#export MG_MQ_HOST=127.0.1.1
#export MG_MQ_USER=garage
#export MG_MQ_PASSWORD=feIT5558idRO
#export MG_MONGO_HOST=127.0.1.1
#export MG_MONGO_SSL=nocert
#export MG_MONGO_USER=garage
#export MG_MONGO_PASSWORD=valHONK331ro

#SENSEUR_NO=25
#SENSEUR_PIN=24

#GARAGE_NO_SENSEUR=25
#GARAGE_PIN=24

PARAMS=""

# Ajouter parametre pour senseur AM2302 au besoin
if [ ! -z GARAGE_NO_SENSUER ]; then
  PARAMS="$PARAMS --am2302 $SENSEUR_NO $SENSEUR_PIN "
fi

echo "Commande: $SCRIPT_PYTHON $PARAMS $COMMAND"
#$SCRIPT_PYTHON $PARAMS $COMMAND
