#!/usr/bin/env python3

from RF24 import *
from RF24Network import *
from RF24Mesh import *

from struct import unpack

import binascii
import datetime
import json
import traceback
import time

from mgraspberry.raspberrypi.ProtocoleVersion7 import AssembleurPaquets, Paquet0, PaquetDemandeDHCP, PaquetReponseDHCP
from mgraspberry.raspberrypi.RF24Mesh import ReserveDHCP

# radio setup for RPi B Rev2: CS0=Pin 24
# radio = RF24(RPI_V2_GPIO_P1_15, RPI_V2_GPIO_P1_24, BCM2835_SPI_SPEED_8MHZ)
radio = RF24(RPI_V2_GPIO_P1_22, RPI_V2_GPIO_P1_24, BCM2835_SPI_SPEED_8MHZ)
network = RF24Network(radio)
mesh = RF24Mesh(radio, network)

radio.begin()
# radio.setAutoAck(True)
# radio.enableDynamicPayloads()
# radio.setRetries(15, 15)

mesh.setNodeID(0)
# mesh.begin(0x7d, RF24_250KBPS)  # Canal prod
mesh.begin(0x48, RF24_2MBPS)  # Canal test
# mesh.begin(0x65, RF24_1MBPS)  # Canal dev
# radio.setPALevel(RF24_PA_HIGH) # Power Amplifier
radio.setPALevel(RF24_PA_LOW) # Power Amplifier
radio.printDetails()


reception_par_nodeId = dict()
reserve_dhcp = ReserveDHCP()


def transmettre_response_dhcp(node_id_reponse, node_id_assigne):

    paquet = PaquetReponseDHCP(node_id_assigne)
    message = paquet.encoder()
    for essai in range(0, 20):
        reponse = mesh.write(message, ord('d'), node_id_reponse)
        mesh.update()
        mesh.DHCP()
        if not reponse:
            print("Erreur transmission reponse %s" % str(reponse))
            mesh.update()
            processNetwork()
            time.sleep(0.01)
        else:
            break

def processNetwork():
        try:
            header, payload = network.peek(8)
            taille_buffer = 24
            if chr(header.type) == '2':
                taille_buffer = 48
            header, payload = network.read(taille_buffer)
            print("Recu data addr: %s. Taille payload: %s" % (oct(header.from_node), len(payload)))
            if chr(header.type) == 'M':
                print("Rcv {} from 0{:o}".format(unpack("h", payload)[0], header.from_node))
            elif chr(header.type) == 'P':
                fromNodeId = mesh.getNodeID(header.from_node)
                paquet0 = Paquet0(header, payload)
                message = AssembleurPaquets(paquet0)
                reception_par_nodeId[fromNodeId] = message
                print("Paquet0 from node ID: %s (mesh addr: %s), %s" % (str(fromNodeId), oct(paquet0.from_node), str(paquet0)))
                print("Paquet0 bin: %s" % binascii.hexlify(payload))
            elif chr(header.type) == 'p':
                fromNodeId = mesh.getNodeID(header.from_node)
                assembleur = reception_par_nodeId.get(fromNodeId)
                if assembleur is not None:
                    complet = assembleur.recevoir(header, payload)
                    if complet:
                        message = assembleur.assembler()
                        message = json.dumps(message, indent=2)
                        print("Message complet: \n%s" % message)
                        del reception_par_nodeId[fromNodeId]
                else:
                    print("Message dropped, paquet 0 inconnu pour nodeId:%d" % fromNodeId)
            elif chr(header.type) == 'D':
                fromNodeId = mesh.getNodeID(header.from_node)
                paquet = PaquetDemandeDHCP(header, payload, fromNodeId)

                # On utilise le node id actuel (pour repondre) comme suggestion
                node_id_suggere = paquet.node_id_reponse
                node_id_reserve = reserve_dhcp.reserver(paquet.uuid, node_id_suggere)
                print("Transmission DHCP reponse nodeId: %d (reponse vers %d)" % (node_id_reserve, node_id_suggere))

                # On transmet la reponse
                transmettre_response_dhcp(node_id_suggere, node_id_reserve)
            elif chr(header.type) == '2':
                print('Paquet double (%d): %s' % (len(payload), binascii.hexlify(payload).decode('utf-8')))
                fromNodeId = mesh.getNodeID(header.from_node)
                assembleur = reception_par_nodeId.get(fromNodeId)
                if assembleur is not None:
                    complet = assembleur.recevoir(header, payload)
                    if complet:
                        message = assembleur.assembler()
                        message = json.dumps(message, indent=2)
                        print("Message complet: \n%s" % message)
                        del reception_par_nodeId[fromNodeId]
                else:
                    print("Message dropped, paquet 0 inconnu pour nodeId:%d" % fromNodeId)
        except Exception as e:
            print("Erreur reception message: %s" % str(e))
            traceback.print_exc()


while 1:
    mesh.update()
    mesh.DHCP()

    while network.available():
        processNetwork()

