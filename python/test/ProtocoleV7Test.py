import unittest
import binascii
from struct import unpack

from mgraspberry.raspberrypi.ProtocoleVersion7 import PaquetReponseDHCP, PaquetOneWireTemperature

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

    def testDecoderTemperatureOneWire(self):
        data = bytes([0x07, 0x05, 0x01, 0x01, 0x00,
                 0x28, 0x54, 0xab, 0x79, 0x97, 0x11, 0x03, 0x0c,
                 0x42, 0x01, 0x55, 0x05, 0x7f, 0xa5, 0xa5, 0x66, 0xbd, 0x00, 0x00, 0x00])
        paquet = PaquetOneWireTemperature(0x0123, data)
        print(str(paquet))