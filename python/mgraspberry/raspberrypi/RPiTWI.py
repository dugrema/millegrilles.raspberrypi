# Module pour appareils TWI (I2C) sur le RaspberryPi

import time
import datetime
import logging
from threading import Thread

import smbus

from millegrilles.dao.Configuration import TransactionConfiguration
from millegrilles.dao.DocumentDAO import MongoDAO
from mgdomaines.appareils.SenseursPassifs import SenseursPassifsConstantes
from millegrilles import Constantes

class LcdHandler:
    # Define some device parameters
    I2C_ADDR = 0x27  # I2C device address
    LCD_WIDTH = 16  # Maximum characters per line

    # Define some device constants
    LCD_CHR = 1  # Mode - Sending data
    LCD_CMD = 0  # Mode - Sending command

    LCD_LINE_1 = 0x80  # LCD RAM address for the 1st line
    LCD_LINE_2 = 0xC0  # LCD RAM address for the 2nd line
    LCD_LINE_3 = 0x94  # LCD RAM address for the 3rd line
    LCD_LINE_4 = 0xD4  # LCD RAM address for the 4th line

    LCD_BACKLIGHT_ON = 0x08  # On
    LCD_BACKLIGHT_OFF = 0x00  # Off

    ENABLE = 0b00000100  # Enable bit

    # Timing constants
    E_PULSE = 0.0005
    E_DELAY = 0.0005

    def __init__(self):
        self.lines = dict()
        self.lines[0] = "Initialising"
        self.lines[1] = "0%"
        self.LCD_BACKLIGHT = LcdHandler.LCD_BACKLIGHT_ON
        self.bus = None

    def initialise(self):
        self.bus = smbus.SMBus(1)  # Rev 2 Pi uses 1

        # Initialise display
        self.lcd_byte(0x33, LcdHandler.LCD_CMD)  # 110011 Initialise
        self.lcd_byte(0x32, LcdHandler.LCD_CMD)  # 110010 Initialise
        self.lcd_byte(0x06, LcdHandler.LCD_CMD)  # 000110 Cursor move direction
        self.lcd_byte(0x0C, LcdHandler.LCD_CMD)  # 001100 Display On,Cursor Off, Blink Off
        self.lcd_byte(0x28, LcdHandler.LCD_CMD)  # 101000 Data length, number of lines, font size
        self.lcd_byte(0x01, LcdHandler.LCD_CMD)  # 000001 Clear display
        time.sleep(LcdHandler.E_DELAY)

    # Close LCD, shut down the backlight. Write "Stopped".
    def close(self):
        self.lcd_string("Stopped", LcdHandler.LCD_LINE_1)
        self.lcd_string("", LcdHandler.LCD_LINE_2)
        time.sleep(LcdHandler.E_DELAY)

        self.LCD_BACKLIGHT = LcdHandler.LCD_BACKLIGHT_OFF
        self.lcd_byte(0x01, LcdHandler.LCD_CMD)  # 000001 Clear display
        time.sleep(LcdHandler.E_DELAY)

    def lcd_byte(self, bits, mode):
        # Send byte to data pins
        # bits = the data
        # mode = 1 for data
        #        0 for command

        bits_high = mode | (bits & 0xF0) | self.LCD_BACKLIGHT
        bits_low = mode | ((bits << 4) & 0xF0) | self.LCD_BACKLIGHT

        # High bits
        self.bus.write_byte(LcdHandler.I2C_ADDR, bits_high)
        self.lcd_toggle_enable(bits_high)

        # Low bits
        self.bus.write_byte(LcdHandler.I2C_ADDR, bits_low)
        self.lcd_toggle_enable(bits_low)

    def lcd_toggle_enable(self, bits):
        # Toggle enable
        time.sleep(LcdHandler.E_DELAY)
        self.bus.write_byte(LcdHandler.I2C_ADDR, (bits | LcdHandler.ENABLE))
        time.sleep(LcdHandler.E_PULSE)
        self.bus.write_byte(LcdHandler.I2C_ADDR, (bits & ~LcdHandler.ENABLE))
        time.sleep(LcdHandler.E_DELAY)

    def lcd_string(self, message, line):
        # Send string to display

        message = message.ljust(LcdHandler.LCD_WIDTH, " ")

        self.lcd_byte(line, LcdHandler.LCD_CMD)

        for i in range(LcdHandler.LCD_WIDTH):
            self.lcd_byte(ord(message[i]), LcdHandler.LCD_CHR)


class DataHandler(Thread):
    location_mapping = dict()
    location_mapping["Cuisine"] = "Int"
    location_mapping["Patio"] = "Ext"

    def __init__(self, configuration=None, document_dao=None):
        self._configuration = configuration
        self._document_dao = document_dao
        self._document_donnees = None  # Document qui est mis a jour par Mongo
        self._document_configuration = None  # Document de configuration de l'ecran
        self._thread = None
        self._lcd_handler = LcdHandler()
        self._active = False

    # Starts thread and runs the process
    def start(self):
        # Verifier s'il faut charger la configuration et le DAO (si la classe est executee independamment)
        if self._configuration is None:
            self._configuration = TransactionConfiguration()
            self._configuration.loadEnvironment()

        if self._document_dao is None:
            self._document_dao = MongoDAO(self._configuration)
            self._document_dao.connecter()

        # Demarrer ecran LCD
        self._lcd_handler.initialise()

        self._thread = Thread(target=self.run)
        self._active = True
        self._thread.start()
        print("HubNRF24L: nRF24L thread started successfully")

    def charger_document_donnees(self):
        collection = self._document_dao.get_collection(SenseursPassifsConstantes.COLLECTION_NOM)
        select = {
            SenseursPassifsConstantes.TRANSACTION_NOEUD: 'cuisine.maple.mdugre.info',
            Constantes.DOCUMENT_INFODOC_LIBELLE: SenseursPassifsConstantes.LIBELLE_DOCUMENT_NOEUD
        }
        resultat = collection.find_one(select)
        if resultat is not None:
            self._document_dao = resultat

    def close(self):
        self._active = False

    def preparer_tendance(self, location):
        location_data = self.data.get(location)
        if location_data is not None:
            tendance = self.dao.get_changement_pression(location)
            location_data["tendance"] = tendance

    def run(self):
        while self.active:
            lecture_int = self.dataHandler.data.get("Cuisine")
            if lecture_int is not None and len(lecture_int) > 0:
                logging.debug("Lecture int RUN: %s" % lecture_int)
                self.afficher_lecture(lecture_int, LcdHandler.LCD_LINE_1)

            lecture_ext = self.dataHandler.data.get("Patio")
            if lecture_ext is not None and len(lecture_ext) > 0:
                logging.debug("Lecture ext RUN: %s" % lecture_ext)
                self.afficher_lecture(lecture_ext, LcdHandler.LCD_LINE_2)

            # Attente pour affichage
            time.sleep(10)

            # Afficher pression atmospherique
            if lecture_ext is not None:
                self.afficher_pression(lecture_ext)
            time.sleep(5)

            # Afficher heure courante
            self.afficher_date(LcdHandler.LCD_LINE_1)
            compteur = 0
            while compteur < 5:
                self.afficher_heure(LcdHandler.LCD_LINE_2)
                compteur = compteur + 1
                time.sleep(1)

    def afficher_lecture(self, lecture, ligne):
        logging.debug("afficher_lecture: %s" % lecture)
        try:
            contenu = "{location}:{temperature:2.1f}C/{humidite:2.0f}%".format(**lecture)
            #  print contenu
            self._lcd_handler.lcd_string(contenu, ligne)
        except Exception as e:
            logging.exception("Erreur afficher_lecture")
            logging.error("----")

    def afficher_pression(self, lecture):
        logging.debug("afficher_pression: %s" % lecture)
        try:
            if lecture.get("pression") is not None:
                contenu = "Press: {pression:3.1f}kPa{tendance}".format(**lecture)
                self._lcd_handler.lcd_string(contenu, lcdHandler.LCD_LINE_1)
        except Exception as e:
            logging.exception("Erreur afficher_pression")
            logging.error("----")

    # Afficher date courante
    def afficher_date(self, ligne):
        ts = time.time()
        timestamp = datetime.datetime.fromtimestamp(ts)
        datestring = timestamp.strftime('%Y-%m-%d')
        self._lcd_handler.lcd_string(datestring, ligne)

    # Afficher heure courante
    def afficher_heure(self, ligne):
        ts = time.time()
        timestamp = datetime.datetime.fromtimestamp(ts)
        timestring = timestamp.strftime('%H:%M:%S')
        self._lcd_handler.lcd_string(timestring, ligne)
