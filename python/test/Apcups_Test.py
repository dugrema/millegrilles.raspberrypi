from mgraspberry.raspberrypi.Apcups import ApcupsdCollector
import logging
import time

class TestApc:

    def __init__(self):
        self.apc = ApcupsdCollector(no_senseur=4, pipe_path='/home/mathieu/pipe', hostname='192.168.2.5')
        self.apc.connecter()

    def test_data(self):
        self.apc.collect()

    def test_events(self):
        data = self.apc.get_evenements()
        print('Events: %s' % str(data))

    def ecouter_evenements(self):
        self.apc.ecouter_evenements()

    def transmettre_evenements(self):
        self.apc.transmettre_evenements()

    def transmettre_etat(self):
        self.apc.transmettre_etat()

    def deconnecter(self):
        self.apc.deconnecter()

def tester():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('mgraspberry').setLevel(logging.DEBUG)
    logging.getLogger('millegrilles').setLevel(logging.DEBUG)

    test_apc = TestApc()
    # test_apc.test_data()
    # test_apc.test_events()
    # test_apc.ecouter_evenements()
    # test_apc.transmettre_evenements()
    # test_apc.transmettre_etat()

    time.sleep(15)

    test_apc.deconnecter()


# Demarrer le test
tester()
