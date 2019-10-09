from struct import pack, unpack

import binascii
import datetime

VERSION_PROTOCOLE = 7

TYPE_REQUETE_DHCP = 0x1
TYPE_REPONSE_DHCP = 0x2

class Paquet:

    def __init__(self, header, data: bytes):
        self.__header = header
        self.__data = data

        self.version = None
        self.type_message = None

        self._parse()

    def _parse(self):
        self.version = self.data[0]
        self.type_message = self.data[1:3]

    def assembler(self):
        raise NotImplementedError()

    @property
    def data(self):
        return self.__data


class Paquet0(Paquet):

    def __init__(self, header, data: bytes):
        self.uuid = None
        self.nombrePaquets = None
        super().__init__(header, data)

    def _parse(self):
        super()._parse()
        self.uuid = self.data[5:21]
        self.nombrePaquets = unpack('h', self.data[3:5])[0]

    def __str__(self):
        return 'Paquet0 UUID: %s, type: %s, nombrePaquets: %s' % (
            binascii.hexlify(self.uuid).decode('utf-8'),
            binascii.hexlify(self.type_message).decode('utf-8'),
            self.nombrePaquets
        )


class PaquetDemandeDHCP(Paquet):

    def __init__(self, header, data: bytes, from_node_id):
        self.node_id_reponse = from_node_id
        self.__node_uuid = None
        super().__init__(header, data)

    def _parse(self):
        super()._parse()
        self.uuid = bytes(self.data[3:19])


class PaquetPayload(Paquet):

    def __init__(self, header, data: bytes):
        self.__noPaquet = None
        super().__init__(header, data)

    def _parse(self):
        super()._parse()
        self.__noPaquet = unpack('H', self.data[3:5])[0]

    @property
    def noPaquet(self):
        return self.__noPaquet


class PaquetTP(PaquetPayload):
    def __init__(self, header, data: bytes):
        self.temperature = None
        self.pression = None
        super().__init__(header, data)

    def _parse(self):
        super()._parse()
        th_values = unpack('hH', self.data[5:9])
        temperature = th_values[0]
        pression = th_values[1]

        if temperature == -32768:
            self.temperature = None
        else:
            self.temperature = float(temperature) / 10.0
        if pression == 0xFF:
            self.pression = None
        else:
            self.pression = float(pression) / 100.0

    def assembler(self):
        return {
            'type': 'tp',
            'temperature': self.temperature,
            'pression': self.pression
        }

    def __str__(self):
        return 'Temperature {}, Pression {}'.format(self.temperature, self.pression)


class PaquetTH(PaquetPayload):
    def __init__(self, header, data: bytes):
        self.temperature = None
        self.pression = None
        super().__init__(header, data)

    def _parse(self):
        super()._parse()
        th_values = unpack('hH', self.data[5:9])
        temperature = th_values[0]
        humidite = th_values[1]

        if temperature == -32768:
            self.temperature = None
        else:
            self.temperature = float(temperature) / 10.0
        if humidite == 0xFF:
            self.humidite = None
        else:
            self.humidite = float(humidite) / 10.0

    def assembler(self):
        return {
            'type': 'th',
            'temperature': self.temperature,
            'humidite': self.humidite
        }

    def __str__(self):
        return 'Temperature {}, Humidite {}'.format(self.temperature, self.humidite)


class PaquetPower(PaquetPayload):
    def __init__(self, header, data: bytes):
        self.millivolt = None
        self.reserve = None
        self.alerte = None
        super().__init__(header, data)

    def _parse(self):
        super()._parse()
        th_values = unpack('IBB', self.data[5:11])
        millivolt = th_values[0]
        reserve = th_values[1]
        self.alerte = th_values[2]

        if millivolt == 0xFFFFFFFF:
            self.millivolt = None
        else:
            self.millivolt = millivolt
        if reserve == 0xFF:
            self.reserve = None
        else:
            self.reserve = reserve

    def assembler(self):
        return {
            'type': 'batterie',
            'millivolt': self.millivolt,
            'reserve': self.reserve,
            'alerte': self.alerte,
        }

    def __str__(self):
        return 'Millivolt {}, Reserve {}, Alerte {}'.format(self.millivolt, self.reserve, self.alerte)


class PaquetOneWire(PaquetPayload):

    def __init__(self, header, data: bytes):
        self.adresse_onewire = None
        self.data_onewire = None
        super().__init__(header, data)

    def _parse(self):
        super()._parse()
        self.adresse_onewire = self.data[5:13]
        self.data_onewire = self.data[13:25]

    def assembler(self):
        return {
            'type': 'onewire',
            'adresse': binascii.hexlify(self.adresse_onewire).decode('utf-8'),
            'data': binascii.hexlify(self.data_onewire).decode('utf-8'),
        }

    def __str__(self):
        return 'OneWire adresse {}, data {}'.format(
            binascii.hexlify(self.adresse_onewire).decode('utf-8'),
            binascii.hexlify(self.data_onewire).decode('utf-8')
        )


class PaquetOneWireTemperature(PaquetOneWire):

    def __init__(self, header, data: bytes):
        self.temperature = None
        super().__init__(header, data)

    def _parse(self):
        super()._parse()
        self.decoder_temperature()

    def assembler(self):
        return {
            'type': 'onewire/temperature',
            'adresse': binascii.hexlify(self.adresse_onewire).decode('utf-8'),
            'temperature': self.temperature,
        }

    def decoder_temperature(self):
        val = self.data[13:15]
        if bytes(val) == bytes([0xFF, 0xFF]):
            self.temperature = None  # Lecture nulle
        else:
            temp_val = unpack('h', val)[0]
            self.temperature = temp_val / 16

    def __str__(self):
        return 'OneWire adresse {}, temperature {}, data {}'.format(
            binascii.hexlify(self.adresse_onewire).decode('utf-8'),
            self.temperature,
            binascii.hexlify(self.data_onewire).decode('utf-8'),
        )


class AssembleurPaquets:

    def __init__(self, paquet0: Paquet0):
        self.__paquet0 = paquet0
        self.__timestamp_debut = datetime.datetime.utcnow()

        self.__paquets = list()
        self.__paquets.append(paquet0)

    def recevoir(self, header, data: bytes):
        """
        Recoit un nouveau paquet de payload. Retourne True quand tous les paquets sont recus.
        :param data:
        :return: True si tous les paquets ont ete recus
        """
        paquet = AssembleurPaquets.map(header, data)
        print("Paquet: %s" % str(paquet))
        self.__paquets.append(paquet)

        if self.__paquet0.nombrePaquets == len(self.__paquets):
            return True

        return False

    def assembler(self):
        dict_message = {
            'uuid': binascii.hexlify(self.__paquet0.uuid).decode('utf-8'),
            'timestamp': int(self.__timestamp_debut.timestamp()),
            'senseurs': [s.assembler() for s in self.__paquets[1:]]
        }

        return dict_message


    @staticmethod
    def map(header, data: bytes):
        type_message = unpack('H', data[1:3])[0]

        paquet = None
        if type_message == 0x102:
            paquet = PaquetTH(header, data)
        elif type_message == 0x103:
            paquet = PaquetTP(header, data)
        elif type_message == 0x104:
            paquet = PaquetPower(header, data)
        elif type_message == 0x105:
            paquet = PaquetOneWireTemperature(header, data)

        return paquet


class PaquetTransmission:

    def __init__(self, type_message: int):
        self.type_message = type_message

    def encoder(self):
        return None


class PaquetReponseDHCP(PaquetTransmission):

    def __init__(self, node_id: int):
        super().__init__(TYPE_REPONSE_DHCP)
        self.node_id = node_id

    def encoder(self):
        message = pack('=BHB', VERSION_PROTOCOLE, TYPE_REPONSE_DHCP, self.node_id)
        message = message + bytes(24-len(message))  # Padding a 24
        return message
