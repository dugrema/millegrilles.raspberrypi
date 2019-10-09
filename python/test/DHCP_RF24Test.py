import unittest

from mgraspberry.raspberrypi.RF24Mesh import ReserveDHCP

class TestDHCP(unittest.TestCase):

    def setUp(self) -> None:
        self.reserve = ReserveDHCP()

        self.uuid1 = 0x00000001
        self.uuid2 = 0x00000002
        self.uuid3 = 0x00000003
        self.uuid4 = 0x00000004
        self.uuid5 = 0x00000005

    def test_node_inconnu(self):
        nodeid_uuid1 = self.reserve.get_node_id(self.uuid1)
        self.assertIsNone(nodeid_uuid1)

        node_id = self.reserve.reserver(self.uuid1, 1)
        print("Node ID assigne pour inconnu: %d" % node_id)
        self.assertGreater(node_id, 1)

    def test_node_assigne(self):
        node_id = self.reserve.reserver(self.uuid1, 1)
        node_id_recov = self.reserve.get_node_id(self.uuid1)
        self.assertEqual(node_id, node_id_recov)

    def test_node_supplementaire(self):
        node_id_1 = self.reserve.reserver(self.uuid1, 1)
        node_id_2 = self.reserve.reserver(self.uuid2, 1)
        print("Node ID assigne pour inconnu: %d, %d" % (node_id_1, node_id_2))
        self.assertNotEqual(node_id_1, node_id_2)

    def test_node_suggere(self):
        node_id = self.reserve.reserver(self.uuid1, 27)
        self.assertEqual(27, node_id)

    def test_deux_nodes_suggere_meme(self):
        node_id_27 = self.reserve.reserver(self.uuid1, 27)
        self.assertEqual(27, node_id_27)

        node_id_n27 = self.reserve.reserver(self.uuid2, 27)
        self.assertNotEqual(27, node_id_n27)
