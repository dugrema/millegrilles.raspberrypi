# Module qui permet de demarrer les appareils sur un Raspberry Pi
import traceback
import argparse
import signal
import time

from threading import Event


class DemarreurRaspberryPi:

    def __init__(self):
        self._parser = argparse.ArgumentParser(description="Demarrer des appareils MilleGrilles sur Raspberry Pi")
        self._args = None

        self._affichage_lcd = None
        self._hub_nrf24l01 = None
        self._am2302 = None

        self._chargement_reussi = False  # Vrai si au moins un module a ete charge
        self._stop_event = Event()
        self._stop_event.set()  # Set initiale, faire clear pour activer le processus

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

    def run_monitor(self):
        if self._chargement_reussi:
            self._stop_event.clear()  # Permettre de bloquer sur le stop_event.

        while not self._stop_event.is_set():
            # Faire verifications de fonctionnement, watchdog, etc...

            # Sleep
            self._stop_event.wait(10)

    def fermer(self):
        self._stop_event.set()

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
        self._affichage_lcd = AffichagePassifTemperatureHumiditePressionLCD2Lignes()
        self._chargement_reussi = True

    def inclure_nrf24l01(self):
        print("Activer nRF24L01")
        from mgraspberry.raspberrypi.NRF24L import HubNRF24L
        self._hub_nrf24l01 = HubNRF24L()
        self._chargement_reussi = True

    def inclure_am2302(self):
        pin = self._args.am2302[0]
        print("Activer AS2302 sur pin %d" % pin)
        from mgraspberry.raspberrypi.AdafruitDHT import ThermometreAdafruitGPIO
        self._am2302 = ThermometreAdafruitGPIO(pin=pin)
        self._chargement_reussi = True


# **** MAIN ****
def exit_gracefully(signum, frame):
    print("Arret de DemarreurRaspberryPi signum: %d" % signum)
    demarreur.fermer()


def main():
    # Faire le relai des signaux OS
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    try:
        demarreur.parse()
        demarreur.setup()
        demarreur.run_monitor()
    except Exception as e:
        print("Erreur %s" % e)
        traceback.print_exc()
        demarreur.print_help()
    finally:
        print("Main termine, on ferme les modules")
        demarreur.fermer()


if __name__=="__main__":
    demarreur = DemarreurRaspberryPi()
    main()
