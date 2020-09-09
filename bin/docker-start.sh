#!/bin/bash

sudo mkdir -p /var/opt/millegrilles/data
sudo chown mathieu:mathieu /var/opt/millegrilles/data

docker run -it \
  --env "MG_IDMG=JPtGcNcFSkfSdw49YsDpQHKxqTHMitpbPZW17a2JC54T" \
  --env "MG_MQ_HOST=192.168.2.131" \
  --env "MG_MQ_PORT=5673" \
  --env "MG_MQ_SSL=on" \
  --env "MG_MQ_AUTH_CERT=on" \
  --env "MG_MQ_CERTFILE=/run/secrets/cert.pem" \
  --env "MG_MQ_KEYFILE=/run/secrets/key.pem" \
  --env "MG_MQ_CA_CERTS=/run/secrets/millegrille.cert.pem" \
  --env "MG_NOEUD_ID=db5d7936-660b-493a-8052-a475b56e8040" \
  --env "MG_CONFIG=/opt/millegrilles/config" \
  --env "MG_MQ_EXCHANGE_DEFAUT=2.prive" \
  --mount type=volume,src=millegrille-secrets,target=/run/secrets \
  --mount type=bind,src=/var/opt/millegrilles/data,target=/var/opt/millegrilles/data \
  --privileged --rm \
  --name senseurspassifs_rpi \
  dugremat/millegrilles_senseurspassifs_rpi:armv7l_1.31.4 \
  -m mgraspberry.raspberrypi.Demarreur --debug --rf24master --am2302 24 nofork
