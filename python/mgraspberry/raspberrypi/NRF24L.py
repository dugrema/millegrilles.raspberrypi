import time
import RF24
import logging

from threading import Thread

from mgdomaines.appareils import ProtocoleSenseursPassifsNRF24l

logger = logging.getLogger(__name__)


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
        self.open_radio()
        self._callback_soumettre = callback_soumettre
        self.thread = Thread(target=self.run)
        self.thread.start()
        logger.info("HubNRF24L: nRF24L thread started successfully")

    def run(self):

        # Flag pour dire que le module est pret et active
        self.active = True

        # Boucle principale d'execution
        while self.active:
            try:
                while not self.radio.available():
                    time.sleep(0.05)

                if self.radio.available():
                    receive_payload = bytes(self.radio.read(11))
                    # print("HubNRF24L: We got data, length %d" % (len(receive_payload)))

                    resultat_dict = ProtocoleSenseursPassifsNRF24l.convertir(receive_payload)
                    if resultat_dict is not None:
                        # print("HubNRF24L: Recu: %s" % resultat_dict)

                        try:
                            self._callback_soumettre(resultat_dict)
                        except Exception:
                            logger.exception("HubNRF24L: Error sending callback message")
                    else:
                        logger.warning("HubNRF24L: Erreur lecture (convertisseur)")

            except Exception as e:
                logger.exception("HubNRF24L: Error processing radio message")

    # Close all connections and the radio
    def fermer(self):
        self.active = False
        try:
            self.radio.stopListening()
            self.radio = None
        except Exception as e:
            logger.warn("HubNRF24L: Error closing radio: %s" % str(e))