from mgraspberry.raspberrypi.AdafruitDHT import ThermometreAdafruitGPIO
from mgdomaines.appareils import ProducteurTransactionSenseursPassifs
import time

class testAM2302:

    def __init__(self):
        # Note: garage pin=24, cuisine=18
        self._reader = ThermometreAdafruitGPIO(no_senseur=0, pin=18, intervalle_lectures=5)
        self._reader._callback_soumettre = self.callback
        self._producteur = ProducteurTransactionSenseursPassifs()
        self._producteur.connecter()

    def test_lire1(self):
        self._reader.lire()

    def test_thread(self):
        self._reader.start(self.callback)
        time.sleep(30)
        self._reader.fermer()

    def callback(self, dict_message):
        print("%s" % str(dict_message))
        self._producteur.transmettre_lecture_senseur(dict_message)

print("Demarrage test")
test = testAM2302()
test.test_lire1()
test.test_thread()
test._producteur.deconnecter()
print("Main termine")