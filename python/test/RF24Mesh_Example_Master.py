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


def lire_th(data):

    th_values = unpack('hH', data[4:8])
    temperature = th_values[0]
    humidite = th_values[1]

    if temperature == -32768:
        temperature = None
    else:
        temperature = float(temperature) / 10.0
    if humidite == 0xFF:
        humidite = None
    else:
        humidite = float(humidite) / 10.0

    print('Temp: {}, Humidite: {}'.format(temperature, humidite))


def lire_tp(data):

    th_values = unpack('hH', data[4:8])
    temperature = th_values[0]
    pression = th_values[1]

    if temperature == -32768:
        temperature = None
    else:
        temperature = float(temperature) / 10.0
    if pression == 0xFF:
        pression = None
    else:
        pression = float(pression) / 100.0

    print('Temp: {}, Pression: {}'.format(temperature, pression))


def lire_power(data):

    th_values = unpack('IBB', data[4:10])
    millivolt = th_values[0]
    reserve = th_values[1]
    alerte = th_values[2]

    if millivolt == 0xFFFFFFFF:
        millivolt = None
    if reserve == 0xFF:
        reserve = None

    print('Millivolt: {}, Reserve: {}, Alerte: {}'.format(millivolt, reserve, alerte))


def lire_mv(data):
    mv_values = unpack('LLLL', data[4:20])
    print("Millivolt: {}, {}, {}, {}".format(mv_values[0], mv_values[1], mv_values[2], mv_values[3]))


def routage_type_message(data):
    commande = unpack('H', data[2:4])[0]
    if commande == 0x102:
        lire_th(data)
    elif commande == 0x103:
        lire_tp(data)
    elif commande == 0x104:
        lire_power(data)
    else:
        raise ValueError("Type message inconnu %s" % hex(commande))


while 1:
    mesh.update()
    mesh.DHCP()

    while network.available():
        header, payload = network.read(24)
        print("Taille payload: %s" % len(payload))
        if chr(header.type) == 'M':
            print("Rcv {} from 0{:o}".format(unpack("h", payload)[0], header.from_node))
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
        else:
            print("Rcv bad type {} from 0{:o}".format(header.type,header.from_node));


