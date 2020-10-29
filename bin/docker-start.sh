#!/bin/bash

# IMAGE=dugremat/millegrilles_senseurspassifs_rpi:armv7l_1.31.4
IMAGE=docker.maceroc.com/millegrilles_senseurspassifs_rpi:armv7l_1.34.2

sudo mkdir -p /var/opt/millegrilles/data
sudo chown mathieu:mathieu /var/opt/millegrilles/data

export MG_NOEUD_ID="de85cd60-39d6-454e-b903-e5381f0634e7"
export MG_IDMG="QME8SjhaCFySD9qBt1AikQ1U7WxieJY2xDg2JCMczJST"
#export RF24_PA=1

CERTS=/home/mathieu/mgdev/certs
export MG_MQ_PORT=5673
export MG_MQ_CA_CERTS=$CERTS/pki.millegrille.cert
export MG_MQ_KEYFILE=$CERTS/pki.monitor.key.20201028191025
export MG_MQ_CERTFILE=$CERTS/pki.monitor.cert.20201028191025
export MG_MQ_SSL=on
export MG_MQ_AUTH_CERT=on
export MG_MQ_EXCHANGE_DEFAUT="2.prive"

docker run -it \
  --env "MG_IDMG=$MG_IDMG" \
  --env "MG_MQ_PORT=$MG_MQ_PORT" \
  --env "MG_MQ_SSL=on" \
  --env "MG_MQ_AUTH_CERT=on" \
  --env "MG_MQ_CERTFILE=/run/secrets/cert.pem" \
  --env "MG_MQ_KEYFILE=/run/secrets/key.pem" \
  --env "MG_MQ_CA_CERTS=/run/secrets/millegrille.cert.pem" \
  --env "MG_NOEUD_ID=$MG_NOEUD_ID" \
  --env "MG_CONFIG=/opt/millegrilles/config" \
  --env "MG_MQ_EXCHANGE_DEFAUT=2.prive" \
  --env "RF24_PA=1" \
  --add-host="mq:192.168.2.131" \
  --mount type=volume,src=millegrille-secrets,target=/run/secrets \
  --mount type=bind,src=/var/opt/millegrilles/data,target=/var/opt/millegrilles/data \
  --privileged --rm \
  --name senseurspassifs_rpi \
  --entrypoint /usr/local/bin/python3.8 \
  $IMAGE \
  -m mgraspberry.raspberrypi.Demarreur --debug --dev --rf24master --am2302 18 --lcdsenseurs nofork


#  -m mgraspberry.raspberrypi.Demarreur --debug --dev --rf24master nofork
#  -m mgraspberry.raspberrypi.Demarreur --debug --dev --rf24master --am2302 18 --lcdsenseurs nofork
#  -m mgraspberry.raspberrypi.Demarreur --debug --rf24master --am2302 18 --lcdsenseurs nofork

