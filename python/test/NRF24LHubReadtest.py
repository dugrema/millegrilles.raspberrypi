from mgraspberry.raspberrypi.AppareilsRaspberryPi import HubNRF24L
from mgdomaines.appareils.SenseursPassifs import ProducteurTransactionSenseursPassifs
import time

class NRF24LHubReadTest:

    def __init__(self):
        self._hub = HubNRF24L()

    def test_demarrage(self):
        self._reader.lire()

    def test_thread(self):
        pass

    def callback(self, dict_message):
        print("%s" % str(dict_message))
        #self._producteur.transmettre_lecture_senseur(dict_message)

print("Demarrage test")
test = NRF24LHubReadTest()
test.test_demarrage()
test.test_thread()
print("Main termine")