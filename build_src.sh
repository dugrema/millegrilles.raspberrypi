#!/bin/bash
set -e

source image_info.txt

echo "Nom build : $NAME"

mkdir -p git

if [ -d git/millegrilles.consignation.python ]; then
	git -C git/millegrilles.consignation.python pull
else
	git -C git/ clone -b 1.34 --single-branch ssh://docker.maceroc.com/git/millegrilles.consignation.python
fi 
