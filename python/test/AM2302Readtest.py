from millegrilles.raspberrypi.AppareilsRaspberryPi import ThermometreAdafruitGPIO


class testAM2302:

    def __init__(self):
        self._reader = ThermometreAdafruitGPIO(no_senseur=0)

    def test(self):
        self._reader._callback_soumettre = self.callback
        self._reader.lire()

    def callback(self, dict_message):
        print("%s" % str(dict_message))


test = testAM2302()
test.test()
