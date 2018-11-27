#!/bin/bash

FICHIER_CONFIG=/usr/local/etc/mg-appareils.conf
SCRIPT_PYTHON=/usr/local/bin/mgraspberrypi.py
COMMAND=$1

if [ ! -f $FICHIER_CONFIG ]; then
  echo "Le fichier de configuration est introuvable: $FICHIER_CONFIG"
  exit 1
fi

source $FICHIER_CONFIG

PARAMS=""

# Ajouter parametre pour senseur AM2302 au besoin
if [ ! -z GARAGE_NO_SENSUER ]; then
  PARAMS="$PARAMS --am2302 $SENSEUR_NO $SENSEUR_PIN "
fi

echo "Commande: $SCRIPT_PYTHON $PARAMS $COMMAND"
$SCRIPT_PYTHON $PARAMS $COMMAND
