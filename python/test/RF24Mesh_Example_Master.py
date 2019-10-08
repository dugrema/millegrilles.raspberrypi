#!/usr/bin/env python3

from RF24 import *
from RF24Network import *
from RF24Mesh import *

from struct import unpack

import binascii
import datetime
import json
import traceback

from mgraspberry.raspberrypi.ProtocoleVersion7 import AssembleurPaquets, Paquet0, PaquetDemandeDHCP, PaquetReponseDHCP
from mgraspberry.raspberrypi.RF24DHCP import ReserveDHCP

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
reserve_dhcp = ReserveDHCP()


def transmettre_response_dhcp(node_id_reponse, node_id_assigne):

    paquet = PaquetReponseDHCP(node_id_assigne)
    message = paquet.encoder()
    reponse = mesh.write(message, 'd', 24, node_id_reponse)
    print("Reponse ecriture: %s" % str(reponse))
    if not reponse:
        print("Erreur transmission reponse")


while 1:
    mesh.update()
    mesh.DHCP()

    while network.available():
        try:
            header, payload = network.read(24)
            print("Taille payload: %s" % len(payload))
            if chr(header.type) == 'M':
                print("Rcv {} from 0{:o}".format(unpack("h", payload)[0], header.from_node))
            elif chr(header.type) == 'P':
                fromNodeId = mesh.getNodeID(header.from_node)
                paquet0 = Paquet0(header, payload)
                message = AssembleurPaquets(paquet0)
                reception_par_nodeId[fromNodeId] = message
                print("Paquet0 from node ID: %s, %s" % (str(fromNodeId), str(paquet0)))
                print("Paquet0 bin: %s" % binascii.hexlify(payload))
            elif chr(header.type) == 'p':
                fromNodeId = mesh.getNodeID(header.from_node)
                assembleur = reception_par_nodeId[fromNodeId]
                complet = assembleur.recevoir(header, payload)
                if complet:
                    message = assembleur.assembler()
                    message = json.dumps(message, indent=2)
                    print("Message complet: \n%s" % message)
                    del reception_par_nodeId[fromNodeId]
            elif chr(header.type) == 'd':
                fromNodeId = mesh.getNodeID(header.from_node)
                paquet = PaquetDemandeDHCP(header, payload, fromNodeId)

                # On utilise le node id actuel (pour repondre) comme suggestion
                node_id_suggere = paquet.node_id_reponse
                node_id_reserve = reserve_dhcp.reserver(paquet.uuid, node_id_suggere)

                # On transmet la reponse
        except Exception as e:
            print("Erreur reception message: %s" % str(e))
            print(e)
            # traceback.print_exception(Exception, 'test', tb=e)
