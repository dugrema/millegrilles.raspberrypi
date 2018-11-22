# Module pour les classes d'appareils utilises avec un Raspberry Pi (2, 3).
import sys
import traceback
import time
import Adafruit_DHT  # https://github.com/adafruit/Adafruit_Python_DHT.git
import RF24

from threading import Thread

from mgdomaines.appareils.ProtocoleSenseurs import ProtocoleSenseursPassifsNRF24l


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

        # Verifier que les valeurs ne sont pas erronees
        if 0 <= humidite <= 100 and -50 < temperature < 50:
            self._callback_soumettre(dict_message)
        else:
            print("ThermometreAdafruitGPIO: Erreur de lecture DHT erronnee, valeurs hors limites: %s" % str(dict_message))

    def start(self, callback_soumettre):
        self._callback_soumettre = callback_soumettre
        self._active = True

        # Demarrer thread
        self._thread = Thread(target=self.run)
        self._thread.start()
        print("ThermometreAdafruitGPIO: thread started successfully")

    def fermer(self):
        self._active = False

    def run(self):
        while self._active:
            try:
                self.lire()
            except:
                print("ThermometreAdafruitGPIO: Erreur lecture AM2302")
                traceback.print_exc(file=sys.stdout)
            finally:
                time.sleep(self._intervalle_lectures)


# Dependences
# RF24-Master.zip: https://tmrh20.github.io/RF24/Python.html
#   - sudo apt-get install python-dev libboost-python-dev
#   - sudo apt-get install python-setuptools
#   - build RF24-Master.zip C++
#   - ./setup.py build  (RF24-Master.zip - python)
#   - sudo ./setup.py install
class HubNRF24L:

    def __init__(self):
        self.active = False
        self.irq_gpio_pin = None
        self.radio = None
        self._callback_soumettre = None
        self.pipes = None
        self.receiverPipes = None
        self.thread = None

    def open_radio(self):

        # Preparation de la radio
        self.radio = RF24.RF24(RF24.RPI_V2_GPIO_P1_22, RF24.BCM2835_SPI_CS0, RF24.BCM2835_SPI_SPEED_8MHZ)

        self.pipes = [0xF0F0F0F0E1, 0x316b6e69E0]
        self.receiverPipes = [0xE1, 0xE2, 0xE3, 0xE4]

        self.radio.begin()
        self.radio.setRetries(5, 15)
        self.radio.setDataRate(RF24.RF24_250KBPS)

        self.radio.openReadingPipe(1, self.pipes[1])
        pipe_counter = 2
        for rpipe in self.receiverPipes:
            self.radio.openReadingPipe(pipe_counter, rpipe)
            pipe_counter += 1

        self.radio.startListening()

        self.radio.printDetails()

    # Starts thread and runs the process
    def start(self, callback_soumettre):
        self._callback_soumettre = callback_soumettre
        self.thread = Thread(target=self.run)
        self.thread.start()
        print("HubNRF24L: nRF24L thread started successfully")

    def run(self):

        # Flag pour dire que le module est pret et active
        self.active = True

        # Boucle principale d'execution
        while self.active:
            try:
                while not self.radio.available():
                    time.sleep(0.05)

                if self.radio.available():
                    receive_payload = self.radio.read(11)
                    print("HubNRF24L: We got data, length %d" % (len(receive_payload)))

                    resultat_dict = ProtocoleSenseursPassifsNRF24l.convertir(receive_payload)
                    if resultat_dict is not None:
                        print("HubNRF24L: Recu: %s" % resultat_dict)

                        try:
                            self._callback_soumettre(resultat_dict)
                        except:
                            print("HubNRF24L: Error sending callback message")
                    else:
                        print("HubNRF24L: Erreur lecture (convertisseur)")

            except Exception as e:
                print("HubNRF24L: Error processing radio message %s" % str(e))

    # Close all connections and the radio
    def close(self):
        self.active = False
        try:
            self.radio.stopListening()
            self.radio = None
        except Exception as e:
            print("HubNRF24L: Error closing radio: %s" % str(e))
