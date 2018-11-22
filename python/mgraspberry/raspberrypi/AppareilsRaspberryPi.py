# Module pour les classes d'appareils utilises avec un Raspberry Pi (2, 3).
import sys
import traceback
import time
import Adafruit_DHT  # https://github.com/adafruit/Adafruit_Python_DHT.git

from threading import Thread


# Thermometre AM2302 connecte sur une pin GPIO
# Dependances:
#   - Adafruit package Adafruit_DHT
class ThermometreAdafruitGPIO:

    def __init__(self, no_senseur, pin=24, sensor=Adafruit_DHT.AM2302, intervalle_lectures=50):
        self._no_senseur = no_senseur
        self._pin = pin
        self._sensor = sensor
        self._intervalle_lectures = intervalle_lectures
        self._callback_soumettre = None
        self._active = False
        self._thread = None

    def lire(self):
        humidite, temperature = Adafruit_DHT.read_retry(self._sensor, self._pin)

        dict_message = {
            'version': 6,
            'senseur': self._no_senseur,
            'temps_lecture': int(time.time()),
            'temperature': round(temperature, 1),
            'humidite': round(humidite, 1)
        }

        self._callback_soumettre(dict_message)

    def start(self, callback_soumettre):
        self._callback_soumettre = callback_soumettre
        self._active = True

        # Demarrer thread
        self._thread = Thread(target=self.run)
        self._thread.start()
        print("ThermometreAdafruitGPIO thread started successfully")

    def fermer(self):
        self._active = False

    def run(self):
        while self._active:
            try:
                self.lire()
            except:
                print("Erreur lecture AM2302")
                traceback.print_exc(file=sys.stdout)
            finally:
                time.sleep(self._intervalle_lectures)
