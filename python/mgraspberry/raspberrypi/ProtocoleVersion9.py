from struct import pack, unpack
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

import binascii
import datetime
import logging

VERSION_PROTOCOLE = 9

class TypesMessages:
    
    TYPE_PAQUET0      = 0x0
    TYPE_PAQUET_IV    = 0xFFFE
    TYPE_PAQUET_FIN   = 0xFFFF
    TYPE_REQUETE_DHCP = 0x1
    TYPE_REPONSE_DHCP = 0x2
    TYPE_BEACON_DHCP  = 0x3
    MSG_TYPE_REPONSE_ACK  = 0x9

    MSG_TYPE_CLE_APPAREIL_1 = 0x4
    MSG_TYPE_CLE_APPAREIL_2 = 0x5
    MSG_TYPE_CLE_SERVEUR_1  = 0x6
    MSG_TYPE_CLE_SERVEUR_2  = 0x7
    MSG_TYPE_NOUVELLE_CLE   = 0x8
    MSG_TYPE_REPONSE_ACK    = 0x9
        
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
        self.type_message = self.data[4:6]

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
        self.type_transmission = unpack('H', self.data[6:8])[0]
        self.uuid = self.data[8:24]

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
        self.uuid = bytes(self.data[6:22])

    def assembler(self):
        return dict()


class PaquetPayload(Paquet):

    def __init__(self, data: bytes):
        self.__no_paquet = None
        super().__init__(data)

    def _parse(self):
        super()._parse()
        self.__no_paquet = unpack('H', self.data[2:4])[0]

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
        return 'Paquet IV : %s, no paquet: %d' % (
            binascii.hexlify(self.iv).decode('utf-8'),
            self.no_paquet
        )
        
    def assembler(self):
        return dict()
        

class PaquetFin(PaquetPayload):

    def __init__(self, data: bytes):
        self.tag = None
        self.nb_paquets = None
        super().__init__(data)

    @property
    def no_paquet(self):
        return self.nb_paquets

    def _parse(self):
        super()._parse()
        self.nb_paquets = unpack('H', self.data[6:8])[0]
        self.tag = self.data[8:24]

    def __str__(self):
        # binascii.hexlify(self.tag).decode('utf-8'),
        return 'Paquet Fin tag: %s, nb paquets: %d' % (
            binascii.hexlify(self.tag),
            self.nb_paquets
        )
        
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

    def __init__(self, paquet0: Paquet0, info_appareil = None):
        self.__paquet0 = paquet0
        self.__info_appareil = info_appareil
        self.__timestamp_debut = datetime.datetime.now()
        self.__tag = None
        self.__tag_calcule = None
        self.__iv = None

        self.__paquets = dict()
        self.__paquets[0] = paquet0
        
        self.__cipher = None
        
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def recevoir(self, data: bytes):
        """
        Recoit un nouveau paquet de payload. Retourne True quand tous les paquets sont recus.
        :param data:
        :return: True si tous les paquets ont ete recus
        """
        paquet = self.map(data)
        if paquet is not None:
            self.__logger.debug("Paquet: %s" % str(paquet))
            self.__paquets[paquet.no_paquet] = paquet

            if isinstance(paquet, PaquetIv):
                self.__iv = paquet.iv
                
                if self.__info_appareil is not None:
                    cle_partagee = self.__info_appareil.get('cle_partagee')
                    if cle_partagee is not None:
                        # Activer cipher
                        self.__cipher = AES.new(cle_partagee, AES.MODE_EAX, nonce=self.__iv)
                    
                        # Ajouter donnees auth (paquet 0, 22 bytes)
                        self.__cipher.update(self.__paquets[0].data[0:22])
                    else:
                        self.__logger.warning("Cle partagee non disponible")
                else:
                    self.__logger.warning("Cle partage non disponible - aucune info appareil")

            if isinstance(paquet, PaquetFin):
                self.__tag = paquet.tag
                return True

        else:
            self.__logger.error("Paquet non decodable")

        return False

    def assembler(self):
        """
        :throws ValueError: Si tag ne correspond pas
        """
        liste_ordonnee = list()
        for idx in range(1, len(self.__paquets)):
            liste_ordonnee.append(self.__paquets[idx])
            
        if self.__cipher is not None:
            # Verifier le tag (hash)
            self.__cipher.verify(self.__tag)
            # except ValueError:
            #     self.__logger.error("Tags (hash) ne correspondent pas")

        dict_message = {
            'uuid_senseur': binascii.hexlify(self.__paquet0.uuid).decode('utf-8'),
            'timestamp': int(self.__timestamp_debut.timestamp()),
            'senseurs': [s.assembler() for s in liste_ordonnee],
            'mesh_address': self.__paquet0.from_node,
        }

        paquet_ack = PaquetACKTransmission(self.__paquet0.from_node, self.__tag)

        return dict_message, paquet_ack
        
    @property
    def doit_decrypter(self):
        return self.__iv is not None
        
    @property
    def type_transmission(self):
        return self.__paquet0.type_transmission

    def map(self, data: bytes):
        no_paquet, type_message = unpack('HH', data[2:6])
        self.__logger.debug("Mapping noPaquet : %d, type paquet : %d" % (no_paquet, type_message))
        
        paquet = None
        if no_paquet == TypesMessages.TYPE_PAQUET_FIN:
            paquet = PaquetFin(data)
        elif self.doit_decrypter:
            # Decrypter data avant le mapping
            # S'assurer de decrypter en ordre et une seule fois
            if self.__cipher is not None:
                if self.__paquets.get(no_paquet-1) is not None and self.__paquets.get(no_paquet) is None:
                    self.__logger.debug("Contenu crypte recu : %s" % binascii.hexlify(data[6:]))
                    # Les 4 premiers bytes ne sont pas cryptes
                    data = data[0:4] + self.__cipher.decrypt(data[4:])
                    type_message = unpack('H', data[4:6])[0]
                    self.__logger.debug("Decrypte noPaquet : %d, type paquet : %d" % (no_paquet, type_message))
            else:
                self.__logger.warning("Cipher non disponible pour donnees cryptees")

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
        """
        Genere le message en bytes. Override dans sous-classe pour 
        ajouter le contenu apres le prefixe.
        """
        prefixe = pack('=BHB', VERSION_PROTOCOLE, self.type_message, self.node_id)
        
        return prefixe


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


class PaquetACKTransmission(PaquetTransmission):
    """
    Paquet utilise pour confirmer la reception correcte (ou non)
    d'une transmission.
    :param node_id: Id du noeud
    :param tag: Compute tag (hash) recu, permet de confirmer le message de maniere unique
    :param commande: Commande transmise en piggy-back.
    """

    def __init__(self, node_id: int, tag: bytes, commande: bytes = None):
        super().__init__(TypesMessages.MSG_TYPE_REPONSE_ACK)
        self.node_id = node_id
        self.tag = tag
        self.commande = commande

    def encoder(self):
        prefixe = super().encoder()
        message = prefixe + bytes([self.node_id])
        if self.tag is not None:
            message = message + self.tag
        if self.commande is not None:
            message = message + self.commande
        message = message + bytes(32-len(message))  # Padding a 32
        return message


class PaquetReponseDHCP(PaquetTransmission):

    def __init__(self, reseau: bytes, node_id: int, node_uuid: bytes):
        super().__init__(TypesMessages.TYPE_REPONSE_DHCP)
        self.__reseau = reseau
        self.node_id = node_id
        self.node_uuid = node_uuid

    def encoder(self):
        prefixe = super().encoder()
        message = prefixe + self.__reseau
        message = message + bytes(32-len(message))  # Padding a 32
        return message


class PaquetReponseCleServeur1(PaquetTransmission):

    def __init__(self, node_id, clePubliqueServeur):
        super().__init__(TypesMessages.MSG_TYPE_CLE_SERVEUR_1)
        self.__clePubliqueServeur = clePubliqueServeur[0:28]
        self.node_id = node_id

    def encoder(self):
        prefixe = super().encoder()
        message = prefixe + self.__clePubliqueServeur
        
        return message


class PaquetReponseCleServeur2(PaquetTransmission):

    def __init__(self, node_id, clePubliqueServeur):
        super().__init__(TypesMessages.MSG_TYPE_CLE_SERVEUR_2)
        self.__clePubliqueServeur = clePubliqueServeur[28:32]
        self.node_id = node_id

    def encoder(self):
        prefixe = super().encoder()
        message = prefixe + self.__clePubliqueServeur
        message = message + bytes(32-len(message))  # Padding a 32

        return message
