from mgraspberry.raspberrypi.NRF24L import HubNRF24L
from mgdomaines.appareils.SenseursPassifs import ProducteurTransactionSenseursPassifs
import time
import traceback

class NRF24LHubReadTest:

    def __init__(self):
        self._hub = HubNRF24L()
        self._producteur = ProducteurTransactionSenseursPassifs()
        self._producteur.connecter()

    def test_demarrage(self):
        self._hub.open_radio()
        self._hub.start(self.callback)
        time.sleep(300)

    def fermer(self):
        self._hub.close()

    def callback(self, dict_message):
        print("%s" % str(dict_message))
        try:
            self._producteur.transmettre_lecture_senseur(dict_message)
        except Exception as e:
            print("Erreur callback: %s" % str(e))
            traceback.print_exc()

print("Demarrage test")
test = NRF24LHubReadTest()
try:
    test.test_demarrage()
finally:
    test.fermer()
print("Main termine")