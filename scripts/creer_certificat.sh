#!/usr/bin/env bash

if [ -z $1 ]; then
  echo "Il faut fournir le IDMG de la millegrille en parametre"
  exit 1
fi

export IDMG=$1

REP_MILLEGRILLE=/var/opt/millegrilles/$IDMG
CURDATE=`date +%Y%m%d%H%M%S`

REP_CERTS=$REP_MILLEGRILLE/pki/certs
REP_KEYS=$REP_MILLEGRILLE/pki/keys

set =e

echo "Creer reps certs et keys: $REP_CERTS"
mkdir -p $REP_CERTS $REP_KEYS

HOSTNAME=`hostname`

creer_cert_noeud() {
  # Params
  # - TYPE_NOEUD: maitredescles, middleware, deployeur, noeud
  # - EXTENSION: noeud_req_extensions, middleware_req_extensions
  # - PASSWORD: si un mot de passe doit etre genere
  set -e

  mkdir -p $REP_CERTS
  mkdir -p $REP_KEYS
  chmod 700 $REP_KEYS

  TYPE_NOEUD=noeud
  EXTENSION=noeud_req_extensions

  echo "[INFO] Creation certificat $TYPE_NOEUD"

  KEY=$REP_KEYS/${IDMG}_${TYPE_NOEUD}_${HOSTNAME}_${CURDATE}.key.pem
  REQ=$REP_CERTS/${IDMG}_${TYPE_NOEUD}_${HOSTNAME}_${CURDATE}.req.pem
  SUBJECT="/O=$IDMG/OU=$TYPE_NOEUD/CN=$HOSTNAME"

  NOM_NOEUD=$HOSTNAME \
  URL_PUBLIC=$URL_PUBLIC \
  openssl req -newkey rsa:2048 -sha512 -nodes \
              -config ./millegrilles.cnf \
              -out $REQ -outform PEM -keyout $KEY -keyform PEM \
              -reqexts noeud_req_public_extensions \
              -subj $SUBJECT


  ln -sf $KEY $REP_KEYS/${IDMG}_${TYPE_NOEUD}.key.pem

  echo "[OK] Creation requete $TYPE_NOEUD complet"
  echo "Coller la valeur suivante dans CoupDOeil / PKI / Signer un certificat de noeud"
  cat $REQ
}

creer_cert_noeud


