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
if [ ! -z $SENSEUR_NO ]; then
  PARAMS="$PARAMS --am2302 $SENSEUR_NO $SENSEUR_PIN "
fi

if [ ! -z $NRF24 ]; then
  PARAMS="$PARAMS --nrf24"
fi

if [ ! -z "$LCDDOC" ]; then
  PARAMS="$PARAMS --lcddoc $LCDDOC"
fi 

if [ ! -z $NOCONNECT ]; then
  PARAMS="$PARAMS --noconnect"
fi

echo "Commande: $SCRIPT_PYTHON $COMMAND $PARAMS"
$SCRIPT_PYTHON $COMMAND $PARAMS 
