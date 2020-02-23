from struct import pack, unpack

import binascii
import datetime

VERSION_PROTOCOLE = 9

class TypesMessages:
    
    TYPE_PAQUET0      = 0x0
    TYPE_PAQUET_IV    = 0xFFFE
    TYPE_PAQUET_FIN   = 0xFFFF
    TYPE_REQUETE_DHCP = 0x1
    TYPE_REPONSE_DHCP = 0x2
    TYPE_BEACON_DHCP  = 0x3

    MSG_TYPE_CLE_APPAREIL_1 = 0x4
    MSG_TYPE_CLE_APPAREIL_2 = 0x5
    MSG_TYPE_CLE_SERVEUR_1  = 0x6
    MSG_TYPE_CLE_SERVEUR_2  = 0x7
    MSG_TYPE_NOUVELLE_CLE   = 0x8
        
    MSG_TYPE_LECTURES_COMBINEES = 0x101
    MSG_TYPE_LECTURE_TH         = 0x102
    MSG_TYPE_LECTURE_TP         = 0x103
    MSG_TYPE_LECTURE_POWER      = 0x104
    MSG_TYPE_LECTURE_ONEWIRE    = 0x105


class Paquet:
    """
    Paque de donnees recues
    """

    def __init__(self, data: bytes):
        self.__data = data

        self.version = None
        self.type_message = None

        self._parse()

    def _parse(self):
        self.version = self.data[0]
        self.type_message = self.data[2:4]

    def assembler(self):
        raise NotImplementedError()

    @property
    def data(self):
        return self.__data

    @property
    def from_node(self):
        return self.data[1]


class Paquet0(Paquet):

    def __init__(self, data: bytes):
        self.uuid = None
        self.type_transmission = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        self.type_transmission = unpack('H', self.data[4:6])[0]
        self.uuid = self.data[6:22]

    def __str__(self):
        return 'Paquet0 UUID: %s, type: %s' % (
            binascii.hexlify(self.uuid).decode('utf-8'),
            binascii.hexlify(self.type_message).decode('utf-8')
        )
        
    def assembler(self):
        return dict()


class PaquetDemandeDHCP(Paquet):

    def __init__(self, data: bytes):
        self.uuid = None
        super().__init__(data)
        self.cle_publique_debut = None

    def _parse(self):
        super()._parse()
        self.uuid = bytes(self.data[3:19])

    def assembler(self):
        return dict()


class PaquetPayload(Paquet):

    def __init__(self, data: bytes):
        self.__no_paquet = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        self.__no_paquet = unpack('H', self.data[4:6])[0]

    @property
    def no_paquet(self):
        return self.__no_paquet


class PaquetIv(PaquetPayload):

    def __init__(self, data: bytes):
        self.iv = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        self.iv = self.data[6:22]

    def __str__(self):
        return 'Paquet Fin tag: %s, nb paquets: %s' % (
            binascii.hexlify(self.iv).decode('utf-8'),
            binascii.hexlify(self.type_message).decode('utf-8')
        )
        
    def assembler(self):
        return dict()
        

class PaquetFin(PaquetPayload):

    def __init__(self, data: bytes):
        self.tag = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        self.tag = self.data[6:22]

    def __str__(self):
        return 'Paquet Fin tag: %s, nb paquets: %s' % (
            binascii.hexlify(self.tag).decode('utf-8'),
            binascii.hexlify(self.type_message).decode('utf-8')
        )
        
    @property
    def nb_paquets(self):
        return self.no_paquet + 1

    def assembler(self):
        return dict()
        
class PaquetCleAppareil1(PaquetPayload):
    
    def __init__(self, data: bytes):
        self.cle_publique_debut = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        self.cle_publique_debut = self.data[6:32]

    def __str__(self):
        return 'Paquet cle appareil debut: %s' % binascii.hexlify(self.cle_publique_debut)
        
    def assembler(self):
        return {
            'cle_publique_debut': self.cle_publique_debut,
        }
        

class PaquetCleAppareil2(PaquetPayload):
    
    def __init__(self, data: bytes):
        self.cle_publique_fin = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        self.cle_publique_fin = self.data[6:12]

    def __str__(self):
        return 'Paquet cle appareil fin: %s' % (
            str(binascii.hexlify(self.cle_publique_fin)),
        )
        
    def assembler(self):
        return {
            'cle_publique_fin': self.cle_publique_fin,
        }        
        
        
class PaquetTP(PaquetPayload):
    def __init__(self, data: bytes):
        self.temperature = None
        self.pression = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        th_values = unpack('hH', self.data[6:10])
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
    def __init__(self, data: bytes):
        self.temperature = None
        self.pression = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        th_values = unpack('hH', self.data[6:10])
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
    def __init__(self, data: bytes):
        self.millivolt = None
        self.reserve = None
        self.alerte = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        th_values = unpack('IBB', self.data[6:12])
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

    def __init__(self, data: bytes):
        self.adresse_onewire = None
        self.data_onewire = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        self.adresse_onewire = self.data[6:14]
        self.data_onewire = self.data[14:26]

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

    def __init__(self, data: bytes):
        self.temperature = None
        super().__init__(data)

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
        val = self.data[14:16]
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
        self.__timestamp_debut = datetime.datetime.now()
        self.__tag = None
        self.__iv = None

        self.__paquets = dict()
        self.__paquets[0] = paquet0

    def recevoir(self, data: bytes):
        """
        Recoit un nouveau paquet de payload. Retourne True quand tous les paquets sont recus.
        :param data:
        :return: True si tous les paquets ont ete recus
        """
        paquet = AssembleurPaquets.map(data)
        print("Paquet: %s" % str(paquet))
        self.__paquets[paquet.no_paquet] = paquet

        if isinstance(paquet, PaquetIv):
            self.__iv = paquet.iv

        if isinstance(paquet, PaquetFin):
            self.__tag = paquet.tag
            return True

        return False

    def assembler(self):
        liste_ordonnee = list()
        for idx in range(1, len(self.__paquets)):
            liste_ordonnee.append(self.__paquets[idx])

        dict_message = {
            'uuid_senseur': binascii.hexlify(self.__paquet0.uuid).decode('utf-8'),
            'timestamp': int(self.__timestamp_debut.timestamp()),
            'senseurs': [s.assembler() for s in liste_ordonnee],
            'mesh_address': self.__paquet0.from_node,
        }

        return dict_message
        
    @property
    def type_transmission(self):
        return self.__paquet0.type_transmission

    @staticmethod
    def map(data: bytes):
        type_message = unpack('H', data[2:4])[0]

        paquet = None
        if type_message == TypesMessages.TYPE_PAQUET_FIN:
            paquet = PaquetFin(data)
        elif type_message == TypesMessages.TYPE_PAQUET_IV:
            paquet = PaquetIv(data)

        elif type_message == TypesMessages.MSG_TYPE_CLE_APPAREIL_1:
            paquet = PaquetCleAppareil1(data)
        elif type_message == TypesMessages.MSG_TYPE_CLE_APPAREIL_2:
            paquet = PaquetCleAppareil2(data)

        elif type_message == TypesMessages.MSG_TYPE_LECTURE_TH:
            paquet = PaquetTH(data)
        elif type_message == TypesMessages.MSG_TYPE_LECTURE_TP:
            paquet = PaquetTP(data)
        elif type_message == TypesMessages.MSG_TYPE_LECTURE_POWER:
            paquet = PaquetPower(data)
        elif type_message == TypesMessages.MSG_TYPE_LECTURE_ONEWIRE:
            paquet = PaquetOneWireTemperature(data)

        return paquet


class PaquetTransmission:

    def __init__(self, type_message: int):
        self.type_message = type_message

    def encoder(self):
        return None


class PaquetBeaconDHCP(PaquetTransmission):
    """
    Paquet transmis a intervalle reguliers sur une adresse de broadcast
    Contient l'information du serveur (adresse pipe, IDMG)
    """

    def __init__(self, adresse_serveur: bytes):
        super().__init__(TypesMessages.TYPE_BEACON_DHCP)
        self.adresse_serveur = adresse_serveur

    def encoder(self):
        message = pack('=BH', VERSION_PROTOCOLE, TypesMessages.TYPE_BEACON_DHCP) + self.adresse_serveur  # Ajouter idmg plus tard
        message = message + bytes(32-len(message))  # Padding a 32
        return message


class PaquetReponseDHCP(PaquetTransmission):

    def __init__(self, reseau: bytes, node_id: int, node_uuid: bytes):
        super().__init__(TypesMessages.TYPE_REPONSE_DHCP)
        self.__reseau = reseau
        self.node_id = node_id
        self.node_uuid = node_uuid

    def encoder(self):
        adresse_node = pack('=B', self.node_id) + self.__reseau
        message = pack('=BH', VERSION_PROTOCOLE, TypesMessages.TYPE_REPONSE_DHCP)
        message = message + adresse_node
        # message = message + self.node_uuid
        message = message + bytes(32-len(message))  # Padding a 32
        return message