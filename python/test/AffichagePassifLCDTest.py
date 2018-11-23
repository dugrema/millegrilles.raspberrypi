from mgraspberry.raspberrypi.RPiTWI import AffichagePassifTemperatureHumiditePressionLCD2Lignes
from millegrilles.dao.Configuration import TransactionConfiguration
from millegrilles.dao.DocumentDAO import MongoDAO
import time
import traceback


class AfficheurSenseurPassifTemperatureHumiditePressionTest(AffichagePassifTemperatureHumiditePressionLCD2Lignes):

    def __init__(self):
        configuration = TransactionConfiguration()
        configuration.loadEnvironment()
        document_dao = MongoDAO(configuration)
        document_dao.connecter()

        document_ids = ['5bef321b82cc2cb5ab0e33c2', '5bef323482cc2cb5ab0e995d']

        super().__init__(configuration, document_dao, document_ids=document_ids, intervalle_secs=5)

    def test(self):
        for document_id in self.get_documents():
            print("Document charge: %s" % str(self._documents[document_id]))

    def maj_affichage(self, lignes_affichage):
        super().maj_affichage(lignes_affichage)

        # print("maj_affichage: (%d lignes) = %s" % (len(lignes_affichage), str(lignes_affichage)))

        for no in range(0, len(lignes_affichage)):
            print("maj_affichage Ligne %d: %s" % (no+1, str(lignes_affichage[no])))


# Demarrer test

test = AfficheurSenseurPassifTemperatureHumiditePressionTest()
try:
    print("Test debut")
    test.start()

    # test.test()
    time.sleep(61)

    print("Test termine")
except Exception as e:
    print("Erreur main: %s" % e)
    traceback.print_exc()
finally:
    test.fermer()
    test._document_dao.deconnecter()
