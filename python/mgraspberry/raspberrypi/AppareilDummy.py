# Module pour les classes d'appareils utilises avec un Raspberry Pi (2, 3).
import datetime
import logging
import random

from threading import Thread, Event


# Appareil dummy avec lectures temperature, humidite, pression
class AppareilDummy:

    def __init__(self, intervalle_lectures=5):
        self._intervalle_lectures = intervalle_lectures
        self._callback_soumettre = None
        self._stop_event = Event()
        self._thread = None

        self._uuid_senseur = 'abcdef01-2345-4010-a1ed-3a600e179cb7'

        self._stop_event.set()

        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def lire(self):
        temperature = float(random.randrange(-500, 500)) / 10.0
        humidite = float(random.randrange(0, 1000)) / 10.0
        pression = float(random.randrange(9950, 10300)) / 100.0

        dict_message = {
            'uuid_senseur': self._uuid_senseur,
            'timestamp': int(datetime.datetime.now().timestamp()),
            'senseurs': [{
                'type': 'DUMMY',
                'temperature': round(temperature, 1),
                'humidite': round(humidite, 1),
                'pression': round(pression, 2),
            }]
        }

        # Verifier que les valeurs ne sont pas erronees
        self._callback_soumettre(dict_message)

    def start(self, callback_soumettre):
        self._callback_soumettre = callback_soumettre
        self._stop_event.clear()

        # Demarrer thread
        self._thread = Thread(target=self.run)
        self._thread.start()
        self.__logger.info("ThermometreAdafruitGPIO: thread started successfully")

    def fermer(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            try:
                self.lire()
            except:
                self.__logger.exception("ThermometreAdafruitGPIO: Erreur lecture AM2302")
            finally:
                self._stop_event.wait(self._intervalle_lectures)

