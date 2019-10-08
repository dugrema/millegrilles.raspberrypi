import unittest
import binascii
from struct import unpack

from mgraspberry.raspberrypi.ProtocoleVersion7 import PaquetReponseDHCP

class TestPaquetsTransmission(unittest.TestCase):

    def testReponseDHCP(self):
        reponse = PaquetReponseDHCP(0x0002, 27)
        message_encode = reponse.encoder()
        print("Message DHCP response encode: %s" % str(binascii.hexlify(message_encode).decode('utf-8')))

        self.assertEqual(24, len(message_encode))
        self.assertEqual(bytes([0x07, 0x02, 0x00, 0x1b]), message_encode[0:4])

        unpacked = unpack('=BHB', message_encode[0:4])
        self.assertEqual(0x07, unpacked[0])
        self.assertEqual(0x2, unpacked[1])
        self.assertEqual(27, unpacked[2])
