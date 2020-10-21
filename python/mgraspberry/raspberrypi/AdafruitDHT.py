# Module pour les classes d'appareils utilises avec un Raspberry Pi (2, 3).
import sys
import traceback
import datetime
import logging
import Adafruit_DHT  # https://github.com/adafruit/Adafruit_Python_DHT.git

from threading import Thread, Event

logger = logging.getLogger(__name__)


# Thermometre AM2302 connecte sur une pin GPIO
# Dependances:
#   - Adafruit package Adafruit_DHT
class ThermometreAdafruitGPIO:

    def __init__(self, uuid_senseur, pin=24, sensor=Adafruit_DHT.AM2302, intervalle_lectures=15):
        self._uuid_senseur = uuid_senseur
        self._pin = pin
        self._sensor = sensor
        self._intervalle_lectures = intervalle_lectures
        self._callback_soumettre = None
        self._stop_event = Event()
        self._thread = None

        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self._stop_event.set()

    def lire(self):
        humidite, temperature = Adafruit_DHT.read_retry(self._sensor, self._pin)

        self.__logger.debug("Lecture senseur : temperature = %s, humidite = %s" % (temperature, humidite))

        try:
            temperature_round = round(temperature, 1)
        except:
            temperature_round = None

        try:
            humidite_round = round(humidite, 1)
        except:
            humidite_round = None

        timestamp = int(datetime.datetime.now().timestamp())

        dict_message = {
            'uuid_senseur': self._uuid_senseur,
            'senseurs': {
                'dht/%d/temperature' % self._pin: {
                    'valeur': temperature_round,
                    'timestamp': timestamp,
                    'type': 'temperature',
                },
                'dht/%d/humidite' % self._pin: {
                    'valeur': humidite_round,
                    'timestamp': timestamp,
                    'type': 'humidite',
                }
            }
        }

        # Verifier que les valeurs ne sont pas erronees
        if 0 <= humidite <= 100 and -50 < temperature < 50:
            self._callback_soumettre(dict_message)
        else:
            logger.warning("ThermometreAdafruitGPIO: Erreur de lecture DHT erronnee, valeurs hors limites: %s" % str(dict_message))

    def start(self, callback_soumettre):
        self._callback_soumettre = callback_soumettre
        self._stop_event.clear()

        # Demarrer thread
        self._thread = Thread(target=self.run)
        self._thread.start()
        logger.info("ThermometreAdafruitGPIO: thread started successfully")

    def fermer(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            try:
                self.lire()
            except:
                logger.exception("ThermometreAdafruitGPIO: Erreur lecture AM2302")
            finally:
                self._stop_event.wait(self._intervalle_lectures)

