from mgraspberry.raspberrypi.Apcups import ApcupsdCollector
import logging

class TestApc:

    def __init__(self):
        self.apc = ApcupsdCollector()
        config = self.apc.get_default_config()
        config['hostname'] = '192.168.2.5'

    def test_data(self):
        self.apc.collect()

    def test_events(self):
        data = self.apc.get_events()
        print('Events: %s' % str(data))

    def ecouter_evenements(self):
        self.apc.ecouter_evenements()


def tester():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('mgraspberry').setLevel(logging.DEBUG)

    test_apc = TestApc()
    # test_apc.test_data()
    # test_apc.test_events()

    test_apc.ecouter_evenements()


# Demarrer le test
tester()
