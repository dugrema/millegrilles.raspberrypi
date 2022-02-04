#!/bin/env bash

# Demarre docker avec les params qui simulent l'environnement de build

GIT_VOL=~/git
RPI_VOL=~/git/millegrilles.raspberrypi
#DOCKER_IMG=docker.maceroc.com/millegrilles_consignation_python_main:2022.0.0
#DOCKER_IMG=python:3.9
DOCKER_IMG=docker.maceroc.com/millegrilles_senseurspassifs_rpi:aarch64_2022.0.0

docker run --rm -it \
  --privileged \
  --entrypoint /bin/bash \
  $DOCKER_IMG
