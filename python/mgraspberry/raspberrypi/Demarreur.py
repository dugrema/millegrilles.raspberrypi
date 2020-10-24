# Module qui permet de demarrer les appareils sur un Raspberry Pi
import traceback
import logging
import binascii
import json
import os

from uuid import uuid1
import RPi.GPIO as GPIO

from mgraspberry.raspberrypi.Constantes import Constantes
from millegrilles.noeuds.Noeud import DemarreurNoeud


# Activer mode BCM pour les pins
GPIO.setmode(GPIO.BCM)


class DemarreurRaspberryPi(DemarreurNoeud):

    def __init__(
            self,
            pidfile='/run/senseurspassifs.pid',
            stdin='/dev/null',
            stdout='/var/log/millegrilles/senseurspassifs.out',
            stderr='/var/log/millegrilles/senseurspassifs.log'
    ):
        # Call superclass init
        super().__init__(pidfile, stdin, stdout, stderr)

        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger('mgraspberry').setLevel(logging.INFO)
        logging.getLogger('mgdomaines').setLevel(logging.INFO)
        self._logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self._affichage_lcd = None
        self._rf24_server = None
        self._am2302 = None

        self.__uuid = None
        self.__config_noeud = None
        self.__idmg = None
        self.__environnement = 'prod'

    def parse(self):
        # Ajouter arguments specifiques au RaspberryPi
        self._parser.add_argument(
            '--dev', action="store_true", required=False,
            help="Developpement env (canal)"
        )
        self._parser.add_argument(
            '--int', action="store_true", required=False,
            help="Integration env (canal)"
        )
        self._parser.add_argument(
            '--lcdsenseurs', action="store_true", required=False,
            help="Active l'affichage LCD 2 lignes sur TWI smbus"
        )
        self._parser.add_argument(
            '--rf24master', action="store_true", required=False,
            help="Active le hub nRF24L01"
        )
        self._parser.add_argument(
            '--am2302', type=int,
            required=False, help="Active le senseur AM2302 sur pin (en parametre)"
        )
        self._parser.add_argument(
            '--timezone', type=str, required=False,
            help="Timezone pytz pour l'horloge, ex: America/Halifax"
        )

        # Completer le parsing via superclasse
        super().parse()

    def setup_modules(self):
        super().setup_modules()
        self.__idmg = self._contexte.idmg

        self.__uuid = os.environ.get('NOEUD_ID')

        if self._args.dev:
            self.__environnement = 'dev'
        elif self._args.int:
            self.__environnement = 'int'
        else:
            self.__environnement = 'prod'
            
        if self._args.debug:
            logging.getLogger('mgraspberry').setLevel(logging.DEBUG)

        # Charger modules specifiques au raspberrypi.
        if self._args.lcdsenseurs:
            try:
                self.inclure_lcd()
            except Exception as erreur_lcd:
                self._logger.exception("Erreur chargement ecran LCD: %s" % str(erreur_lcd))
                # traceback.print_exc()

        if self._args.rf24master:
            try:
                self.inclure_nrf24l01()
            except Exception as erreur_nrf24:
                self._logger.exception("Erreur chargement hub nRF24L01: %s" % str(erreur_nrf24))
                # traceback.print_exc()

        if self._args.am2302:
            try:
                self.inclure_am2302()
            except Exception as erreur_nrf24:
                self._logger.exception("Erreur chargement AM2302 sur pin %s: %s" % (str(self._args.am2302), str(erreur_nrf24)))
                # traceback.print_exc()

    def fermer(self):
        super().fermer()

        for app in self._appareils:
            try:
                app.fermer()
            except:
                self._logger.exception("Erreur fermeture appareil")

    def inclure_lcd(self):
        self._logger.info("Activer LCD")
        from mgraspberry.raspberrypi.RPiTWI import AffichagePassifLCD2Lignes

        if self._args.timezone is None:
            timezone = self._args.timezone
        else:
            timezone = 'America/Toronto'

        self._affichage_lcd = AffichagePassifLCD2Lignes(self.contexte, horloge_timezone=timezone)
        self._affichage_lcd.start()
        # self._appareils.append(self._affichage_lcd)
        self._chargement_reussi = True

    def inclure_nrf24l01(self):
        self._logger.info("Activer RF24 Server")
        from mgraspberry.raspberrypi.RF24Server import NRF24Server
        self._rf24_server = NRF24Server(self.__idmg, self.__environnement)
        self._rf24_server.start(self.transmettre_lecture_callback)
        self._appareils.append(self._rf24_server)
        self._chargement_reussi = True

    def inclure_am2302(self):
        pin = self._args.am2302
        self._logger.info("Activer AS2302 sur pin %d" % pin)
        from mgraspberry.raspberrypi.AdafruitDHT import ThermometreAdafruitGPIO
        self._am2302 = ThermometreAdafruitGPIO(self.__uuid, pin=pin)
        self._am2302.start(self.transmettre_lecture_callback)
        self._appareils.append(self._am2302)
        self._chargement_reussi = True

    def inclure_dummy(self):
        from mgraspberry.raspberrypi.AppareilDummy import AppareilDummy
        appareil_dummy = AppareilDummy()
        appareil_dummy.start(self.transmettre_lecture_callback)
        self._appareils.append(appareil_dummy)
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
