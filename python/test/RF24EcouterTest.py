from __future__ import print_function

# Module qui permet de demarrer les appareils sur un Raspberry Pi
import traceback
import logging
import os

import RF24
import donna25519
import RPi.GPIO as GPIO

from threading import Thread, Event, Lock
from os import path, urandom, environ
from zlib import crc32
from struct import unpack

import binascii
import json
import datetime
import struct

import logging

type_env = 'dev'

from mgraspberry.raspberrypi.Constantes import Constantes as ConstantesRPi
# from mgraspberry.raspberrypi import ProtocoleVersion9
# from mgraspberry.raspberrypi.ProtocoleVersion9 import VERSION_PROTOCOLE, \
#     AssembleurPaquets, Paquet0, PaquetDemandeDHCP, PaquetBeaconDHCP, PaquetReponseDHCP, TypesMessages

# Activer mode BCM pour les pins - global
GPIO.setmode(GPIO.BCM)


class Constantes(ConstantesRPi):
    MG_CHANNEL_PROD = 0x5e
    MG_CHANNEL_INT = 0x24
    MG_CHANNEL_DEV = 0x0c

    # ADDR_BROADCAST_DHCP = bytes([0x29, 0x0E, 0x92, 0x54, 0x8B])  # Adresse de broadcast du beacon
    ADDR_BROADCAST_DHCP = bytes([0x8B, 0x54, 0x92, 0x0E, 0x29])  # Adresse de broadcast du beacon

    INTERVALLE_BEACON = 0.25

    TRANSMISSION_NB_ESSAIS = 3

    RPI_V2_GPIO_P1_22 = 25
    PIN_IRQ = 24
    BCM2835_SPI_CS0 = 0
    BCM2835_SPI_SPEED_8MHZ = 8000000

    FICHIER_CONFIG_RESEAU = 'senseurspassifs.reseau.conf'
    FICHIER_CONFIG_DHCP = 'senseurspassifs.dhcp.json'


class DemarreurRaspberryPi:

    def __init__(
            self,
            pidfile='/run/senseurspassifs.pid',
            stdin='/dev/null',
            stdout='/var/log/millegrilles/senseurspassifs.out',
            stderr='/var/log/millegrilles/senseurspassifs.log'
    ):
        # Call superclass init
        # super().__init__(pidfile, stdin, stdout, stderr)

        logging.getLogger().setLevel(logging.WARNING)
        self.__logger = logging.getLogger('mgraspberry')
        self.__logger.setLevel(logging.WARN)
        logging.getLogger('mgdomaines').setLevel(logging.WARN)
        self._rf24_server = None

        # Event pour indiquer a la thread de processing qu'on a un message
        self.__event_reception = Event()

        self.__fifo_payload = list()  # FIFO traitement messages
        self.__fifo_transmit = list()  # FIFO d'evenements a transmettre

        self.__event_action = Event()
        self.__lock_radio = Lock()
        self.__lock_reception = Lock()
        self.__thread = None

        self.__radio_PA_level = int(environ.get('RF24_PA') or RF24.RF24_PA_MIN)
        self.__logger.info("Radio PA level : %d" % self.__radio_PA_level)

        self.__radio_pin = int(environ.get('RF24_RADIO_PIN') or Constantes.RPI_V2_GPIO_P1_22)
        self.__radio_irq = int(environ.get('RF24_RADIO_IRQ') or 24)

        if type_env == 'prod':
            self.__channel = Constantes.MG_CHANNEL_PROD
        elif type_env == 'int':
            self.__logger.info("Mode INT")
            self.__channel = Constantes.MG_CHANNEL_INT
        else:
            self.__logger.info("Mode DEV")
            self.__channel = Constantes.MG_CHANNEL_DEV

        self.irq_gpio_pin = None
        self.__radio = None
        self.__event_reception = Event()

        self.__information_appareils_par_uuid = dict()

        self.__intervalle_beacon = datetime.timedelta(seconds=Constantes.INTERVALLE_BEACON)
        self.__prochain_beacon = datetime.datetime.utcnow()

        self.__message_beacon = None

    def start(self):
        self.open_radio()
        self.thread = Thread(name="RF24Radio", target=self.run, daemon=True)
        self.thread.start()

    def open_radio(self):
        self.__logger.info("Ouverture radio sur canal %s" % hex(self.__channel))
        self.__radio = RF24.RF24(self.__radio_pin, Constantes.BCM2835_SPI_CS0, Constantes.BCM2835_SPI_SPEED_8MHZ)

        if not self.__radio.begin():
            raise Exception("Erreur demarrage radio")

        self.__radio.setChannel(self.__channel)
        self.__radio.setDataRate(RF24.RF24_250KBPS)
        self.__radio.setPALevel(self.__radio_PA_level, False)  # Power Amplifier
        self.__radio.setRetries(1, 15)
        self.__radio.setAutoAck(1)
        self.__radio.setCRCLength(RF24.RF24_CRC_16)

        # addresse_serveur = bytes(b'\x00\x00') + self.__adresse_serveur
        # addresse_serveur = self.__formatAdresse(addresse_serveur)
        # self.__radio.openReadingPipe(1, addresse_serveur)
        # self.__logger.info("Address reading pipe 1: %s" % hex(addresse_serveur))
        #
        print("Radio details")
        print( self.__radio.printDetails() )
        print("Fin radio details")

        self.__logger.info("Radio ouverte")
        #
        # # Connecter IRQ pour reception paquets
        # # Masquer TX OK et fail sur IRQ, juste garder payload ready
        self.__radio.maskIRQ(True, True, False)
        GPIO.setup(Constantes.PIN_IRQ, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.__radio_irq, GPIO.FALLING, callback=self.__process_network_messages)

    def recevoir(self, message):
        # Ajouter payload sur liste FIFO
        if len(self.__fifo_payload) < 100:
            with self.__lock_reception:
                self.__fifo_payload.append(message)
        else:
            self.__logger.warning("FIFO reception message plein, message perdu")

        self.__event_reception.set()

    def __transmettre_beacon(self):
        if datetime.datetime.utcnow() > self.__prochain_beacon:
            # self.__logger.debug("Beacon")

            self.__prochain_beacon = datetime.datetime.utcnow() + self.__intervalle_beacon
            try:
                self.__radio.stopListening()
                self.__radio.openWritingPipe(Constantes.ADDR_BROADCAST_DHCP)
                self.__radio.write(self.__message_beacon, True)
            finally:
                self.__radio.startListening()

    def __process_network_messages(self, channel):
        if channel is not None and self.__logger.isEnabledFor(logging.DEBUG):
            self.__logger.debug("Message sur channel %d" % channel)

        with self.__lock_radio:
            while self.__radio.available():
                try:
                    payload = self.__radio.read(32)  # taille_buffer
                    self.recevoir(payload)
                except Exception as e:
                    self.__logger.exception("NRF24MeshServer: Error processing radio message")

    def __formatAdresse(self, adresse: bytes):
        adresse_paddee = adresse + bytes(8 - len(adresse))
        adresse_no = struct.unpack('Q', adresse_paddee)[0]
        return adresse_no

    def run(self):
        Event().wait(5)


# **** MAIN ****
def main():
    print("Demarrage test nRF24 raspberrypi")
    demarreur = DemarreurRaspberryPi()
    demarreur.start()

if __name__ == "__main__":
    main()
