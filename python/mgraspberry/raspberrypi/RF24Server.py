import RF24

from threading import Thread, Event
from os import path, urandom

import binascii
import json
import datetime

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
        self.__intervalle_beacon = datetime.timedelta(seconds=5)
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
        self.__radio = RF24.RF24(RF24.RPI_V2_GPIO_P1_22, RF24.BCM2835_SPI_CS0, RF24.BCM2835_SPI_SPEED_8MHZ)

        self.__radio.begin()
        self.__radio.setChannel(self.__channel)
        self.__radio.setDataRate(RF24.RF24_250KBPS)
        self.__radio.setPALevel(RF24.RF24_PA_MAX)  # Power Amplifier
        # self.__radio.enableDynamicPayloads()
        self.__radio.setRetries(15, 1)
        self.__radio.setAutoAck(1)
        self.__radio.setCRCLength(RF24.RF24_CRC_16)

        self.__radio.printDetails()

    # Starts thread and runs the process
    def start(self, callback_soumettre):
        self.open_radio()
        self._callback_soumettre = callback_soumettre
        self.thread = Thread(target=self.run)
        self.thread.start()
        self.__logger.info("NRF24MeshServer: nRF24L thread started successfully")

    def __process_network_messages(self):
        while self.__radio.available():

            try:
                taille_buffer = self.__radio.getDynamicPayloadSize()
                payload = self.__radio.read(taille_buffer)

                self.__logger.debug("Payload %s bytes\n%s" % (len(payload), binascii.hexlify(payload).decode('utf-8')))
                self.process_paquet_payload(payload)

            except Exception as e:
                self.__logger.exception("NRF24MeshServer: Error processing radio message")
                self.__stop_event.wait(5)  # Attendre 5 secondes avant de poursuivre

    def __executer_cycle(self):
        self.__process_network_messages()

        if datetime.datetime.utcnow() > self.__prochain_beacon:
            self.__prochain_beacon = datetime.datetime.utcnow() + self.__intervalle_beacon
            self.transmettre_beacon()

        self.__stop_event.wait(0.005)  # Throttle le service

    def run(self):

        # Boucle principale d'execution
        while not self.__stop_event.is_set():
            try:
                self.__executer_cycle()
            except Exception as e:
                self.__logger.exception("NRF24Server: Error processing update ou DHCP")
                self.__stop_event.wait(5)  # Attendre 5 secondes avant de poursuivre

    def process_dhcp_request(self, node_id, payload):
        paquet = PaquetDemandeDHCP(payload, node_id)

        # On utilise le node id actuel (pour repondre) comme suggestion
        node_id_suggere = paquet.node_id_reponse
        node_id_reserve = self.__reserve_dhcp.reserver(paquet.uuid, node_id_suggere)
        self.__logger.debug("Transmission DHCP reponse nodeId: %d (reponse vers %d)" % (node_id_reserve, node_id_suggere))

        # On transmet la reponse
        self.transmettre_response_dhcp(node_id_suggere, node_id_reserve)

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
            type_paquet = payload[2:4]

            if type_paquet == TYPE_PAQUET0:
                # Paquet0
                self.process_paquet0(from_node_id, payload)
            elif type_paquet == TYPE_REQUETE_DHCP:
                self.process_dhcp_request(from_node_id, payload)
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

        paquet = PaquetReponseDHCP(node_id_assigne, node_uuid)
        message = paquet.encoder()
        for essai in range(0, 4):
            reponse = self.__radio.write(message)
            if not reponse:
                self.__logger.warning("Erreur transmission reponse %s" % str(reponse))
            else:
                break

    def transmettre_beacon(self):
        self.__radio.openWritingPipe(ADDR_BROADCAST_DHCP)
        self.__radio.stopListening()
        for i in range(0, 5):
            self.__radio.write(self.__message_beacon, True)
        self.__radio.stopListening()

    # Close all connections and the radio
    def fermer(self):
        self.__stop_event.set()
        try:
            self.__radio.stopListening()
            self.__radio = None
        except Exception as e:
            self.__logger.warning("NRF24MeshServer: Error closing radio: %s" % str(e))


class ReserveDHCP:

    def __init__(self, fichier_dhcp: str):
        self.__node_id_by_uuid = dict()
        self.__fichier_dhcp = fichier_dhcp

    def charger_fichier_dhcp(self):
        with open(self.__fichier_dhcp, 'r') as fichier:
            self.__node_id_by_uuid = json.load(fichier)

    def sauvegarder_fichier_dhcp(self):
        with open(self.__fichier_dhcp, 'w') as fichier:
            json.dump(self.__node_id_by_uuid, fichier)

    def get_node_id(self, uuid: bytes):
        node_id = self.__node_id_by_uuid.get(uuid)
        return node_id

    def reserver(self, uuid: bytes, node_id_suggere: int):
        assigner_nouvelle_adresse = True
        node_id = self.get_node_id(uuid)
        suggestion_deja_assigne = node_id_suggere in self.__node_id_by_uuid.values()
        if node_id_suggere is not None:
            if node_id_suggere == 1:
                # On assigne nouvelle adresse
                assigner_nouvelle_adresse = True
            elif node_id == node_id_suggere:
                # Rien a faire
                assigner_nouvelle_adresse = False
            elif suggestion_deja_assigne:
                # La suggestion ne match pas le noeud existant et node_id deja assigne.
                # On determine un nouvel ID.
                assigner_nouvelle_adresse = True
            elif node_id is None:
                # Ok, on assigne le node id suggere
                assigner_nouvelle_adresse = False
                node_id = node_id_suggere
            elif node_id_suggere != node_id and node_id not in self.__node_id_by_uuid.values():
                # On change l'adresse interne, efface l'ancienne
                # On permet au noeud de garder cette adresse (differente)
                del self.__node_id_by_uuid[node_id]
                node_id = node_id_suggere
                assigner_nouvelle_adresse = False
            else:
                # Le node ne correspond pas au UUID, on assigne un nouveau lease
                assigner_nouvelle_adresse = True

        if assigner_nouvelle_adresse:
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
