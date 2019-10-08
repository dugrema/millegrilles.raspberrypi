#!/usr/bin/env python3

from RF24 import *
from RF24Network import *
from RF24Mesh import *

from struct import unpack

import binascii
import datetime
import json

from mgraspberry.raspberrypi.ProtocoleVersion7 import AssembleurPaquets, Paquet0

# radio setup for RPi B Rev2: CS0=Pin 24
# radio = RF24(RPI_V2_GPIO_P1_15, RPI_V2_GPIO_P1_24, BCM2835_SPI_SPEED_8MHZ)
radio = RF24(RPI_V2_GPIO_P1_22, RPI_V2_GPIO_P1_24, BCM2835_SPI_SPEED_8MHZ)
network = RF24Network(radio)
mesh = RF24Mesh(radio, network)

mesh.setNodeID(0)
mesh.begin(62)
radio.setPALevel(RF24_PA_LOW) # Power Amplifier
radio.printDetails()


reception_par_nodeId = dict()

while 1:
    mesh.update()
    mesh.DHCP()

    while network.available():
        header, payload = network.read(24)
        print("Taille payload: %s" % len(payload))
        if chr(header.type) == 'M':
            print("Rcv {} from 0{:o}".format(unpack("h", payload)[0], header.from_node))
        elif chr(header.type) == 'P':
            fromNodeId = mesh.getNodeID(header.from_node)
            paquet0 = Paquet0(payload)
            message = AssembleurPaquets(paquet0)
            reception_par_nodeId[fromNodeId] = message
            print("Paquet0 from node ID: %s, %s" % (str(fromNodeId), str(paquet0)))
            print("Paquet0 bin: %s" % binascii.hexlify(payload))
        elif chr(header.type) == 'p':
            fromNodeId = mesh.getNodeID(header.from_node)
            assembleur = reception_par_nodeId[fromNodeId]
            complet = assembleur.recevoir(payload)
            if complet:
                message = assembleur.assembler()
                message = json.dumps(message, indent=2)
                print("Message complet: \n%s" % message)
                del reception_par_nodeId[fromNodeId]
        else:
            print("Rcv bad type {} from 0{:o}".format(header.type, header.from_node))

