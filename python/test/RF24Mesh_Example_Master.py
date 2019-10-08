#!/usr/bin/env python3

from RF24 import *
from RF24Network import *
from RF24Mesh import *

from struct import unpack

import binascii
import datetime


# radio setup for RPi B Rev2: CS0=Pin 24
# radio = RF24(RPI_V2_GPIO_P1_15, RPI_V2_GPIO_P1_24, BCM2835_SPI_SPEED_8MHZ)
radio = RF24(RPI_V2_GPIO_P1_22, RPI_V2_GPIO_P1_24, BCM2835_SPI_SPEED_8MHZ)
network = RF24Network(radio)
mesh = RF24Mesh(radio, network)

mesh.setNodeID(0)
mesh.begin(87)
radio.setPALevel(RF24_PA_LOW) # Power Amplifier
radio.printDetails()


reception_par_nodeId = dict()


class Paquet:

    def __init__(self, data: bytes):
        self.__data = data

        self.version = None
        self.type_message = None

        self._parse()

    def _parse(self):
        self.version = self.data[0]
        self.type_message = self.data[1:3]

    @property
    def data(self):
        return self.__data


class Paquet0(Paquet):

    def __init__(self, data: bytes):
        self.uuid = None
        self.nombrePaquets = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        self.uuid = binascii.hexlify(self.data[5:22])
        self.nombrePaquets = unpack('h', self.data[3:5])[0]

    def __str__(self):
        return 'Paquet0 UUID: %s, type: %s, nombrePaquets: %s' % (
            binascii.hexlify(self.uuid).decode('utf-8'),
            binascii.hexlify(self.type_message).decode('utf-8'),
            self.nombrePaquets
        )


class PaquetPayload(Paquet):

    def __init__(self, data: bytes):
        self.__noPaquet = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        self.__noPaquet = unpack('H', self.data[3:5])[0]

    @property
    def noPaquet(self):
        return self.__noPaquet


class PaquetTP(PaquetPayload):
    def __init__(self, data: bytes):
        self.temperature = None
        self.pression = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        th_values = unpack('hH', self.data[5:9])
        temperature = th_values[0]
        pression = th_values[1]

        if temperature == -32768:
            self.temperature = None
        else:
            self.temperature = float(temperature) / 10.0
        if pression == 0xFF:
            self.pression = None
        else:
            self.pression = float(pression) / 100.0

    def __str__(self):
        return 'Temperature {}, Pression {}'.format(self.temperature, self.pression)


class PaquetTH(PaquetPayload):
    def __init__(self, data: bytes):
        self.temperature = None
        self.pression = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        th_values = unpack('hH', self.data[5:9])
        temperature = th_values[0]
        humidite = th_values[1]

        if temperature == -32768:
            self.temperature = None
        else:
            self.temperature = float(temperature) / 10.0
        if humidite == 0xFF:
            self.humidite = None
        else:
            self.humidite = float(humidite) / 10.0

    def __str__(self):
        return 'Temperature {}, Humidite {}'.format(self.temperature, self.humidite)


class PaquetPower(PaquetPayload):
    def __init__(self, data: bytes):
        self.millivolt = None
        self.reserve = None
        self.alerte = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        th_values = unpack('IBB', self.data[5:11])
        millivolt = th_values[0]
        reserve = th_values[1]
        self.alerte = th_values[2]

        if millivolt == 0xFFFFFFFF:
            self.millivolt = None
        else:
            self.millivolt = millivolt
        if reserve == 0xFF:
            self.reserve = None
        else:
            self.reserve = reserve

    def __str__(self):
        return 'Millivolt {}, Reserve {}, Alerte {}'.format(self.millivolt, self.reserve, self.alerte)


class MessageAppareil:

    def __init__(self, paquet0: Paquet0):
        self.__paquet0 = paquet0
        self.__timestamp_debut = datetime.datetime.utcnow()

        self.__paquets = list()
        self.__paquets.append(paquet0)

    def recevoir(self, data: bytes):
        """
        Recoit un nouveau paquet de payload. Retourne True quand tous les paquets sont recus.
        :param data:
        :return: True si tous les paquets ont ete recus
        """
        paquet = MessageAppareil.map(data)
        print("Paquet: %s" % str(paquet))
        self.__paquets.append(paquet)

        if self.__paquet0.nombrePaquets == len(self.__paquets):
            return True

        return False

    @staticmethod
    def map(data: bytes):
        type_message = unpack('H', data[1:3])[0]

        paquet = None
        if type_message == 0x102:
            paquet = PaquetTH(data)
        elif type_message == 0x103:
            paquet = PaquetTP(data)
        elif type_message == 0x104:
            paquet = PaquetPower(data)

        return paquet


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
            message = MessageAppareil(paquet0)
            reception_par_nodeId[fromNodeId] = message
            print("Paquet0 from node ID: %s, Paquet0: %s" % (str(fromNodeId), str(paquet0)))
            print("Paquet0 bin: %s" % binascii.hexlify(payload))
        elif chr(header.type) == 'p':
            fromNodeId = mesh.getNodeID(header.from_node)
            complet = reception_par_nodeId[fromNodeId].recevoir(payload)
            if complet:
                print("Message complet")
                del reception_par_nodeId[fromNodeId]
        else:
            print("Rcv bad type {} from 0{:o}".format(header.type, header.from_node));
