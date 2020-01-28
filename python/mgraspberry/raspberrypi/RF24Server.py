import RF24

from threading import Thread, Event
from os import path, urandom

import binascii
import json
import datetime
import struct 

import logging

from mgraspberry.raspberrypi.ProtocoleVersion8 import AssembleurPaquets, Paquet0, PaquetDemandeDHCP, \
    PaquetBeaconDHCP, PaquetReponseDHCP, TYPE_REQUETE_DHCP, TYPE_PAQUET0

MG_CHANNEL_PROD = 0x5e
MG_CHANNEL_INT = 0x1f
MG_CHANNEL_DEV = 0x0c

ADDR_BROADCAST_DHCP = 0x290E92548B  # Adresse de broadcast du beacon


class NRF24Server:

    def __init__(self, idmg: str, type_env='prod'):
        """
        Environnements
        :param idmg: IDMG de la MilleGrille
        :param type_env: prod, int ou dev
        """

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.__idmg = idmg
        self.__type_env = type_env

        self.__stop_event = Event()
        self.reception_par_nodeId = dict()
        self.__assembleur_par_nodeId = dict()

        # Conserver le canal de communication
        if type_env == 'prod':
            self.__channel = MG_CHANNEL_PROD
        elif type_env == 'int':
            self.__channel = MG_CHANNEL_INT
        else:
            self.__channel = MG_CHANNEL_DEV

        self.irq_gpio_pin = None
        self.__radio = None

        self._callback_soumettre = None
        self.thread = None
        self.__configuration = None

        self.__path_configuration = '/opt/millegrilles/etc/%s' % idmg
        self.__reserve_dhcp = ReserveDHCP(path.join(self.__path_configuration, 'rf24dhcp.json'))

        self.__adresse_serveur = None
        self.__adresse_reseau = None
        self.__message_beacon = None
        self.__intervalle_beacon = datetime.timedelta(seconds=2)
        self.__prochain_beacon = datetime.datetime.utcnow()

        self.initialiser_configuration()

    def initialiser_configuration(self):
        # Charger les fichiers de configuration
        try:
            self.__reserve_dhcp.charger_fichier_dhcp()
        except FileNotFoundError:
            self.__logger.info("Initialiser fichier DHCP")
            self.__reserve_dhcp.sauvegarder_fichier_dhcp()

        try:
            with open(path.join(self.__path_configuration, 'rf24server.json'), 'r') as fichier:
                self.__configuration = json.load(fichier)
            self.__logger.info("Charge configuration:\n%s" % json.dumps(self.__configuration))

            adresses = self.__configuration['adresses']
            self.__adresse_serveur = binascii.unhexlify(adresses['serveur'].encode('utf8'))
            self.__adresse_reseau = binascii.unhexlify(adresses['reseau'].encode('utf8'))

        except FileNotFoundError:
            self.__logger.info("Creation d'une nouvelle configuration pour le serveur")
            self.__adresse_serveur = urandom(3)  # Generer 3 bytes pour l'adresse serveur receiving pipe
            self.__adresse_reseau = urandom(4)  # Generer 4 bytes pour l'adresse du reseau
            configuration = {
                'adresses': {
                    'serveur': binascii.hexlify(self.__adresse_serveur).decode('utf8'),
                    'reseau': binascii.hexlify(self.__adresse_reseau).decode('utf8'),
                }
            }
            self.__logger.info("Configuration: %s" % str(configuration))
            with open(path.join(self.__path_configuration, 'rf24server.json'), 'w') as fichier:
                json.dump(configuration, fichier)
            self.__configuration = configuration

        # Preparer le paque beacon (il change uniquement si l'adresse du serveur change)
        self.__message_beacon = PaquetBeaconDHCP(self.__adresse_serveur).encoder()

    def open_radio(self):
        self.__logger.info("Ouverture radio sur canal %d" % self.__channel)
        self.__radio = RF24.RF24(RF24.RPI_V2_GPIO_P1_22, RF24.BCM2835_SPI_CS0, RF24.BCM2835_SPI_SPEED_8MHZ)

        self.__radio.begin()

        self.__radio.setChannel(0x24) # (self.__channel)
        self.__radio.setDataRate(RF24.RF24_250KBPS)
        # self.__radio.setPALevel(RF24.RF24_PA_MAX)  # Power Amplifier
        self.__radio.setPALevel(RF24.RF24_PA_LOW)  # Power Amplifier
        # self.__radio.enableDynamicPayloads()
        self.__radio.setRetries(15, 1)
        self.__radio.setAutoAck(1)
        self.__radio.setCRCLength(RF24.RF24_CRC_16)

        # self.__radio.openWritingPipe(self.__adresse_serveur)
        # self.__radio.openReadingPipe(1, self.__adresse_reseau + bytes(0x0) + bytes(0x0))
        addresseServeur = bytes(b'\x00\x00') + self.__adresse_serveur
        addresseServeur = self.formatAdresse(addresseServeur)
        self.__radio.openReadingPipe(1, addresseServeur)
        self.__logger.info("Address reading pipe 1: %s" % hex(addresseServeur))

        print("Details radio")
        self.__radio.printDetails()
        self.__logger.info("Radio ouverte")

    # Starts thread and runs the process
    def start(self, callback_soumettre):
        self.open_radio()
        self._callback_soumettre = callback_soumettre
        self.thread = Thread(name="RF24Server", target=self.run)
        self.thread.start()
        self.__logger.info("RF24Server: thread started successfully")

    def __process_network_messages(self):
        while self.__radio.available():
            try:
                taille_buffer = self.__radio.getDynamicPayloadSize()
                payload = self.__radio.read(taille_buffer)

                self.__logger.info("Payload %s bytes\n%s" % (len(payload), binascii.hexlify(payload).decode('utf-8')))
                self.process_paquet_payload(payload)

            except Exception as e:
                self.__logger.exception("NRF24MeshServer: Error processing radio message")
                self.__stop_event.wait(5)  # Attendre 5 secondes avant de poursuivre

    def __executer_cycle(self):
        self.__process_network_messages()

        if datetime.datetime.utcnow() > self.__prochain_beacon:
            self.__prochain_beacon = datetime.datetime.utcnow() + self.__intervalle_beacon
            self.transmettre_beacon()

        compteur = 0
        while not self.__radio.available() and compteur < 500:
            self.__stop_event.wait(0.002)  # Throttle le service
            compteur = compteur + 1

    def run(self):
        self.__logger.debug("Run Thread RF24Server")

        # Boucle principale d'execution
        while not self.__stop_event.is_set():
            try:
                self.__executer_cycle()
            except Exception as e:
                self.__logger.exception("NRF24Server: Error processing update ou DHCP")
                self.__stop_event.wait(5)  # Attendre 5 secondes avant de poursuivre

        self.__logger.debug("Fin Run Thread RF24Server")

    def process_dhcp_request(self, payload):
        paquet = PaquetDemandeDHCP(payload)

        # On utilise le node id actuel (pour repondre) comme suggestion
        node_id_reserve = self.__reserve_dhcp.reserver(paquet.uuid)
        self.__logger.debug("Transmission DHCP reponse nodeId: %d (reponse vers %s)" % (node_id_reserve, str(paquet.uuid)))

        # On transmet la reponse
        self.transmettre_response_dhcp(node_id_reserve, paquet.uuid)

    def process_paquet0(self, node_id, payload):
        paquet0 = Paquet0(payload)
        message = AssembleurPaquets(paquet0)
        self.__assembleur_par_nodeId[node_id] = message
        self.__logger.debug("Paquet0 from node ID: %s, %s" % (str(node_id), str(paquet0)))
        self.__logger.debug("Paquet0 bin: %s" % binascii.hexlify(payload))

    def process_paquet_payload(self, payload):
        version = payload[0]
        if version == 8:
            from_node_id = payload[1]
            type_paquet = struct.unpack('H', payload[1:3])[0]
            self.__logger.info("Type paquet: %d" % type_paquet) 

            if type_paquet == TYPE_PAQUET0:
                # Paquet0
                self.process_paquet0(from_node_id, payload)
            elif type_paquet == TYPE_REQUETE_DHCP:
                self.process_dhcp_request(payload)
            else:
                assembleur = self.__assembleur_par_nodeId.get(from_node_id)
                if assembleur is not None:
                    complet = assembleur.recevoir(payload)
                    if complet:
                        message = assembleur.assembler()
                        message_json = json.dumps(message, indent=2)
                        self.__logger.debug("Message complet: \n%s" % message_json)

                        # Transmettre message recu a MQ
                        self._callback_soumettre(message)

                        del self.__assembleur_par_nodeId[from_node_id]
                else:
                    self.__logger.info("Message dropped, paquet 0 inconnu pour nodeId:%d" % from_node_id)
        else:
            self.__logger.warning("Message version non supportee : %d" % version)

    def transmettre_response_dhcp(self, node_id_assigne, node_uuid):

        paquet = PaquetReponseDHCP(self.__adresse_reseau, node_id_assigne, node_uuid)
        message = paquet.encoder()
        self.__logger.info("Transmission paquet DHCP repose nodeId:%d\n%s" % (node_id_assigne, binascii.hexlify(message).decode('utf8')))
        for essai in range(0, 4):
            reponse = self.__radio.write(message)
            if not reponse:
                self.__logger.warning("Erreur transmission reponse %s" % str(reponse))
            else:
                break

    def transmettre_beacon(self):
        self.__logger.info("Transmission beacon %s" % binascii.hexlify(self.__message_beacon).decode('utf8'))
        self.__radio.openWritingPipe(ADDR_BROADCAST_DHCP)
        self.__radio.stopListening()
        # for i in range(0, 3):
        self.__radio.write(self.__message_beacon, True)
        self.__radio.startListening()

    # Close all connections and the radio
    def fermer(self):
        self.__stop_event.set()
        try:
            self.__radio.stopListening()
            self.__radio = None
        except Exception as e:
            self.__logger.warning("NRF24MeshServer: Error closing radio: %s" % str(e))
            
    def formatAdresse(self, adresse: bytes):
        adresse_paddee = adresse + bytes(8-len(adresse))
        adresse_no = struct.unpack('Q', adresse_paddee)[0]
        return adresse_no


class ReserveDHCP:

    def __init__(self, fichier_dhcp: str):
        self.__node_id_by_uuid = dict()
        self.__fichier_dhcp = fichier_dhcp

    def charger_fichier_dhcp(self):
        with open(self.__fichier_dhcp, 'r') as fichier:
            node_id_str_by_uuid = json.load(fichier)

        for uuid_str, value in node_id_str_by_uuid.items():
            uuid_bytes = binascii.unhexlify(uuid_str.encode('utf8'))
            self.__node_id_by_uuid[uuid_bytes] = value

    def sauvegarder_fichier_dhcp(self):

        # Changer la cle de bytes a str
        node_id_str_by_uuid = dict()
        for uuid_bytes, value in self.__node_id_by_uuid.items():
            uuid_str = binascii.hexlify(uuid_bytes).decode('utf8')
            node_id_str_by_uuid[uuid_str] = value

        with open(self.__fichier_dhcp, 'w') as fichier:
            json.dump(node_id_str_by_uuid, fichier)

    def get_node_id(self, uuid: bytes):
        node_id = self.__node_id_by_uuid.get(uuid)
        return node_id

    def reserver(self, uuid: bytes):
        node_id = self.get_node_id(uuid)

        if node_id is None:
            node_id = self._identifier_nouvelle_adresse()

        if node_id is not None:
            self.__node_id_by_uuid[uuid] = node_id
            self.sauvegarder_fichier_dhcp()

        return node_id

    def _identifier_nouvelle_adresse(self):
        """
        Donne la prochaine adresse disponible entre 2 et 254
        Adresse 0xff (255) est pour broadcast, tous les noeuds ecoutent
        :return:
        """

        node_id_list = self.__node_id_by_uuid.values()
        for node_id in range(2, 254):
            if node_id not in node_id_list:
                return node_id

        return None
