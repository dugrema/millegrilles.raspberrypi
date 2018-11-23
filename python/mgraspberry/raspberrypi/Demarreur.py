# Module qui permet de demarrer les appareils sur un Raspberry Pi
import traceback
import argparse


class DemarreurRaspberryPi:

    def __init__(self):
        self._parser = argparse.ArgumentParser(description="Demarrer des appareils MilleGrilles sur Raspberry Pi")
        self._args = None

        self._affichage_lcd = None
        self._hub_nrf24l01 = None
        self._am2302 = None

    def print_help(self):
        self._parser.print_help()

    def parse(self):
        self._parser.add_argument(
            '--lcd', action="store_true", required=False,
            help="Active l'affichage LCD 2 lignes sur TWI smbus"
        )
        self._parser.add_argument(
            '--nrf24', action="store_true", required=False,
            help="Active le hub nRF24L01"
        )
        self._parser.add_argument(
            '--am2302', type=int, nargs=1,
            required=False, help="Active le senseur AM2302 sur pin en parametre"
        )

        self._args = self._parser.parse_args()

    def setup(self):
        if self._args.lcd:
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
                print("Erreur chargement AM2302 sur pin %d: %s" % (self._args.am2302[0], str(erreur_nrf24)))
                traceback.print_exc()

    def inclure_lcd(self):
        print("Activer LCD")
        from mgraspberry.raspberrypi.RPiTWI import AffichagePassifTemperatureHumiditePressionLCD2Lignes
        self._affichage_lcd = AffichagePassifTemperatureHumiditePressionLCD2Lignes()

    def inclure_nrf24l01(self):
        print("Activer nRF24L01")
        from mgraspberry.raspberrypi.NRF24L import HubNRF24L
        self._hub_nrf24l01 = HubNRF24L()

    def inclure_am2302(self):
        pin = self._args.am2302[0]
        print("Activer AS2302 sur pin %d" % pin)
        from mgraspberry.raspberrypi.AdafruitDHT import ThermometreAdafruitGPIO
        self._am2302 = ThermometreAdafruitGPIO(pin=pin)

# **** MAIN ****
demarreur = DemarreurRaspberryPi()
try:
    demarreur.parse()
    demarreur.setup()
except Exception as e:
    print("Erreur %s" % e)
    traceback.print_exc()
    demarreur.print_help()
