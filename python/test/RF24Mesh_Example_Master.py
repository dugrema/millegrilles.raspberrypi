#!/usr/bin/env python3

from RF24 import *
from RF24Network import *
from RF24Mesh import *

from struct import unpack

import uuid
import binascii


# radio setup for RPi B Rev2: CS0=Pin 24
# radio = RF24(RPI_V2_GPIO_P1_15, RPI_V2_GPIO_P1_24, BCM2835_SPI_SPEED_8MHZ)
radio = RF24(RPI_V2_GPIO_P1_22, RPI_V2_GPIO_P1_24, BCM2835_SPI_SPEED_8MHZ)
network = RF24Network(radio)
mesh = RF24Mesh(radio, network)

mesh.setNodeID(0)
mesh.begin(87)
radio.setPALevel(RF24_PA_LOW) # Power Amplifier
radio.printDetails()

commande_precedente = None

def lire_thp(data):

    tph_values = unpack('hHH', data[4:10])
    temperature = float(tph_values[0]) / 10.0
    humidite = float(tph_values[1]) / 10.0
    pression = float(tph_values[2]) / 10.0

    print('Temp: {}, Humidite: {}, Pression: {}'.format(temperature, humidite, pression))


def lire_mv(data):
    mv_values = unpack('LLLL', data[4:20])
    print("Millivolt: {}, {}, {}, {}".format(mv_values[0], mv_values[1], mv_values[2], mv_values[3]))


def routage_type_message(data):
    commande = unpack('H', data[2:4])[0]
    if commande == 0x102:
        lire_thp(data)
    elif commande == 0x103:
        lire_mv(data)
    else:
        raise ValueError("Type message inconnu %s" % hex(commande))


while 1:
    mesh.update()
    mesh.DHCP()

    while network.available():
        header, payload = network.read(24)
        print("Taille payload: %s" % len(payload))
        if chr(header.type) == 'M':
            print("Rcv {} from 0{:o}".format(unpack("h",payload)[0], header.from_node))
        elif chr(header.type) == 'P':
            version = payload[0]
            uuid_appareil = binascii.hexlify(payload[1:17]).decode('utf-8')
            commande = binascii.hexlify(payload[18:20]).decode('utf-8')
            type_nb = unpack('h', payload[20:22])
            nombre_paquets = type_nb[0]

            commande_precedente = commande

            print("Rcv version:{}, UUID:{}, commande:{}, nombre_paquets:{}, from 0{:o}".format(version, uuid_appareil, commande, nombre_paquets, header.from_node))
        elif chr(header.type) == 'p':
            routage_type_message(payload)
            #lire_thp(payload)
            # print("Rcv UUID:{} from 0{:o}".format(unpack("hhhhhhhhhhhhhhhhhhhhhhhh",payload)[0], header.from_node))
        else:
            print("Rcv bad type {} from 0{:o}".format(header.type,header.from_node));


