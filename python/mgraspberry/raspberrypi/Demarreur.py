# Module qui permet de demarrer les appareils sur un Raspberry Pi
import traceback
import argparse
import logging
import binascii
import json

from uuid import uuid1

from threading import Event
from pika.exceptions import ChannelClosed

from millegrilles.dao.Configuration import TransactionConfiguration
from millegrilles.dao.MessageDAO import PikaDAO, ExceptionConnectionFermee
from millegrilles.dao.DocumentDAO import MongoDAO
from millegrilles.domaines.SenseursPassifs import ProducteurTransactionSenseursPassifs
from millegrilles.noeuds.Noeud import DemarreurNoeud

from millegrilles.util.Daemon import Daemon

logger = logging.getLogger(__name__)


class DemarreurRaspberryPi(DemarreurNoeud):

    def __init__(
            self,
            pidfile='/run/mg-demarreur-rpi.pid',
            stdin='/dev/null',
            stdout='/var/log/mg-demarreur-rpi.log',
            stderr='/var/log/mg-demarreur-rpi.err'
    ):
        # Call superclass init
        super().__init__(pidfile, stdin, stdout, stderr)

        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger('mgraspberry').setLevel(logging.INFO)
        self._logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self._affichage_lcd = None
        self._hub_nrf24l01 = None
        self._am2302 = None

        self.__uuid = None
        self.__config_noeud = None

    def parse(self):
        # Ajouter arguments specifiques au RaspberryPi
        self._parser.add_argument(
            '--lcdsenseurs', type=int, nargs='+', required=False,
            help="Active l'affichage LCD 2 lignes sur TWI smbus"
        )
        self._parser.add_argument(
            '--nrf24', action="store_true", required=False,
            help="Active le hub nRF24L01"
        )
        self._parser.add_argument(
            '--am2302', type=int, nargs=1,
            required=False, help="Active le senseur AM2302 sur pin (en parametre)"
        )

        # Completer le parsing via superclasse
        super().parse()

    def setup_modules(self):
        super().setup_modules()

        try:
            with open('/opt/millegrilles/etc/noeud.json', 'r') as fichier:
                config_noeud = json.load(fichier)
        except FileNotFoundError:
            config_noeud = dict()

        if config_noeud.get('uuid') is None:
            config_noeud['uuid'] = binascii.hexlify(uuid1().bytes)
            with open('/opt/millegrilles/etc/noeud.json', 'w') as fichier:
                json.dump(config_noeud, fichier)

        self.__config_noeud = config_noeud
        self.__uuid = config_noeud['uuid']

        # Charger modules specifiques au raspberrypi.
        if self._args.lcdsenseurs:
            try:
                self.inclure_lcd()
            except Exception as erreur_lcd:
                print("Erreur chargement ecran LCD: %s" % str(erreur_lcd))
                traceback.print_exc()

        if self._args.nrf24:
            try:
                self.inclure_nrf24l01()
            except Exception as erreur_nrf24:
                print("Erreur chargement hub nRF24L01: %s" % str(erreur_nrf24))
                traceback.print_exc()

        if self._args.am2302:
            try:
                self.inclure_am2302()
            except Exception as erreur_nrf24:
                print("Erreur chargement AM2302 sur pin %d: %s" % (self._args.am2302, str(erreur_nrf24)))
                traceback.print_exc()

    def fermer(self):
        super().fermer()

        if self._hub_nrf24l01 is not None:
            try:
                self._hub_nrf24l01.fermer()
            except Exception as enrf:
                print("erreur fermeture NRF24L01: %s" % str(enrf))

        if self._affichage_lcd is not None:
            try:
                self._affichage_lcd.fermer()
            except Exception as elcd:
                print("erreur fermeture LCD: %s" % str(elcd))

        if self._am2302 is not None:
            try:
                self._am2302.fermer()
            except Exception as eam:
                print("erreur fermeture AM2302: %s" % str(eam))

    def inclure_lcd(self):
        print("Activer LCD")
        from mgraspberry.raspberrypi.RPiTWI import AffichagePassifTemperatureHumiditePressionLCD2Lignes
        self._affichage_lcd = AffichagePassifTemperatureHumiditePressionLCD2Lignes(
            self.contexte,
            self._args.lcdsenseurs
        )
        self._affichage_lcd.start()
        self._chargement_reussi = True

    def inclure_nrf24l01(self):
        print("Activer nRF24L01")
        from mgraspberry.raspberrypi.NRF24L import HubNRF24L
        self._hub_nrf24l01 = HubNRF24L()
        self._hub_nrf24l01.start(self.transmettre_lecture_callback)
        self._chargement_reussi = True

    def inclure_am2302(self):
        pin = self._args.am2302[1]
        print("Activer AS2302 sur pin %d" % pin)
        from mgraspberry.raspberrypi.AdafruitDHT import ThermometreAdafruitGPIO
        self._am2302 = ThermometreAdafruitGPIO(self.__uuid, pin=pin)
        self._am2302.start(self.transmettre_lecture_callback)
        self._chargement_reussi = True


# **** MAIN ****
def main():
    try:
        demarreur.parse()
        demarreur.executer_daemon_command()
    except Exception as e:
        print("!!! ******************************")
        print("MAIN: Erreur %s" % str(e))
        traceback.print_exc()
        print("!!! ******************************")
        demarreur.print_help()


if __name__ == "__main__":
    demarreur = DemarreurRaspberryPi()
    main()
