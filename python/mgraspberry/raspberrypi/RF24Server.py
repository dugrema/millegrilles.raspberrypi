from __future__ import print_function
import RF24
import RPi.GPIO as GPIO
import donna25519

from threading import Thread, Event, Lock
from os import path, urandom

import binascii
import json
import datetime
import struct

import logging

from mgraspberry.raspberrypi.Constantes import Constantes as ConstantesRPi
from mgraspberry.raspberrypi import ProtocoleVersion9
from mgraspberry.raspberrypi.ProtocoleVersion9 import VERSION_PROTOCOLE, \
    AssembleurPaquets, Paquet0, PaquetDemandeDHCP, PaquetBeaconDHCP, PaquetReponseDHCP, \
    TypesMessages, PaquetReponseCleServeur1, PaquetReponseCleServeur2


GPIO.setmode(GPIO.BCM)

class Constantes(ConstantesRPi):
    MG_CHANNEL_PROD = 0x5e
    MG_CHANNEL_INT = 0x24
    MG_CHANNEL_DEV = 0x0c

    ADDR_BROADCAST_DHCP = 0x290E92548B  # Adresse de broadcast du beacon

    TRANSMISSION_NB_ESSAIS = 10

    RPI_V2_GPIO_P1_22 = 25
    BCM2835_SPI_CS0 = 0
    BCM2835_SPI_SPEED_8MHZ = 8000000


class RadioThread:
    """
    Thread pour la radio. 
    Agit comme iter sur les messages recu.
    """

    def __init__(self, stop_event: Event, type_env='prod'):
        """
        Environnements
        :param idmg: IDMG de la MilleGrille
        :param type_env: prod, int ou dev
        """
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        
        # Event pour indiquer a la thread de processing qu'on a un message
        self.__event_reception = Event()
        self.__stop_event = stop_event

        self.__fifo_payload = list()   # FIFO traitement messages
        self.__fifo_transmit = list()  # FIFO d'evenements a transmettre
        
        self.__event_action = Event()
        self.__lock_radio = Lock()
        self.__lock_reception = Lock()
        self.__thread = None

        self.__radio_PA_level = RF24.RF24_PA_LOW

        if type_env == 'prod':
            self.__channel = Constantes.MG_CHANNEL_PROD
        elif type_env == 'int':
            self.__logger.info("Mode INT")
            self.__channel = Constantes.MG_CHANNEL_INT
            self.__radio_PA_level = RF24.RF24_PA_LOW
        else:
            self.__logger.info("Mode DEV")
            self.__channel = Constantes.MG_CHANNEL_DEV
            self.__radio_PA_level = RF24.RF24_PA_LOW

        self.irq_gpio_pin = None
        self.__radio = None
        self.__event_reception = Event()

        self.__information_appareils_par_uuid = dict()

        self.__intervalle_beacon = datetime.timedelta(seconds=0.25)
        self.__prochain_beacon = datetime.datetime.utcnow()
        
        self.__message_beacon = None

    def start(self):
        self.open_radio()
        self.thread = Thread(name="RF24Radio", target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        self.__logger.info("RF24Radio: thread started successfully")
        try:
            while not self.__stop_event.is_set():
                self.__transmettre_beacon()
                self.__transmettre_paquets()
                self.__event_action.wait(0.1)
        finally:
            self.__logger.info("Arret de la radio")
            radio.stopListening()
            GPIO.cleanup()

    def recevoir(self, message):
        # Ajouter payload sur liste FIFO
        if len(self.__fifo_payload) < 100:
            with self.__lock_reception:
                self.__fifo_payload.append(message)
        else:
            self.__logger.warning("FIFO reception message plein, message perdu")
        
        self.__event_reception.set()
    
    def transmettre(self, paquet: ProtocoleVersion9.PaquetTransmission):
        self.__fifo_transmit.append(paquet)
        self.__event_action.set()
        
    def __transmettre_paquets(self):
        # Clear flag de transmission
        self.__event_action.clear()
        
        while len(self.__fifo_transmit) > 0:
            self.__stop_event.wait(0.05)  # Throttling, wait 50ms to receive data

            paquet = self.__fifo_transmit.pop(0)
            
            # Determiner adresse de transmission
            node_id = paquet.node_id
            if node_id is None or isinstance(paquet, ProtocoleVersion9.PaquetReponseDHCP):
                adresse = Constantes.ADDR_BROADCAST_DHCP
            else:
                # Le premier byte de l'adresse est le node_id
                adresse = bytes([node_id]) + self.__adresse_reseau
                
            reponse = True
            try:
                self.__radio.openWritingPipe(adresse)

                if not reponse:
                    self.__logger.error("Erreur transmission vers : %s" % binascii.hexlify(adresse))
                    break
                
                message = paquet.encoder()
                self.__logger.debug("Transmission paquet nodeId:%d\n%s" % (
                    paquet.node_id, binascii.hexlify(message).decode('utf8')))

                for essai in range(0, Constantes.TRANSMISSION_NB_ESSAIS):
                    with self.__lock_radio:
                        self.__radio.stopListening()
                        # self.__logger.debug("Transmission paquet en cours")
                        reponse = self.__radio.write(message)
                        if reponse:
                            # Transmission reussie
                            self.__logger.debug("Transmission paquet OK")
                            break
                        self.__radio.startListening()
                    self.__stop_event.wait(0.002)  # Wait 2ms between attemps
                
                if not reponse:
                    self.__logger.debug("Transmission paquet ECHEC")
                            
            except Exception:
                self.__logger.exception("Erreur tranmission message vers %s" % str(adresse))
                reponse = False
            finally:
                # S'assurer de redemarrer l'ecoute de la radio
                self.__radio.startListening()

    def open_radio(self):
        self.__logger.info("Ouverture radio sur canal %s" % hex(self.__channel))
        self.__radio = RF24.RF24(Constantes.RPI_V2_GPIO_P1_22, Constantes.BCM2835_SPI_CS0, Constantes.BCM2835_SPI_SPEED_8MHZ)

        if not self.__radio.begin():
            raise Exception("Erreur demarrage radio")

        self.__radio.setChannel(self.__channel)
        self.__radio.setDataRate(RF24.RF24_250KBPS)
        self.__radio.setPALevel(self.__radio_PA_level, False)  # Power Amplifier
        self.__radio.setRetries(5, 3)
        self.__radio.setAutoAck(1)
        self.__radio.setCRCLength(RF24.RF24_CRC_16)

        addresseServeur = bytes(b'\x00\x00') + self.__adresse_serveur
        addresseServeur = self.__formatAdresse(addresseServeur)
        self.__radio.openReadingPipe(1, addresseServeur)
        self.__logger.info("Address reading pipe 1: %s" % hex(addresseServeur))

        # print("Radio details")
        # print( self.__radio.printDetails() )
        # print("Fin radio details")
        
        self.__logger.info("Radio ouverte")

        # Connecter IRQ pour reception paquets
        # Masquer TX OK et fail sur IRQ, juste garder payload ready
        self.__radio.maskIRQ(True, True, False);
        GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(24, GPIO.FALLING, callback=self.__process_network_messages)
    
    def __transmettre_beacon(self):
        if datetime.datetime.utcnow() > self.__prochain_beacon:
            # self.__logger.debug("Beacon")

            self.__prochain_beacon = datetime.datetime.utcnow() + self.__intervalle_beacon
            try:
                self.__radio.stopListening()
                self.__radio.openWritingPipe(Constantes.ADDR_BROADCAST_DHCP)
                self.__radio.write(self.__message_beacon, True)
            finally:
                self.__radio.startListening()
    
    def __process_network_messages(self, channel):
        if channel is not None and self.__logger.isEnabledFor(logging.DEBUG):
            self.__logger.debug("Message sur channel %d" % channel)

        with self.__lock_radio:
            while self.__radio.available():
                try:
                    payload = self.__radio.read(32)  # taille_buffer
                    self.recevoir(payload)
                except Exception as e:
                    self.__logger.exception("NRF24MeshServer: Error processing radio message")
    
    def __formatAdresse(self, adresse: bytes):
        adresse_paddee = adresse + bytes(8-len(adresse))
        adresse_no = struct.unpack('Q', adresse_paddee)[0]
        return adresse_no
        
    def set_adresse_serveur(self, adresse_serveur):
        self.__logger.info("Adresse serveur : %s" % binascii.hexlify(adresse_serveur).decode('utf-8'))
        self.__adresse_serveur = adresse_serveur
        # Preparer le paque beacon (il change uniquement si l'adresse du serveur change)
        self.__message_beacon = PaquetBeaconDHCP(self.__adresse_serveur).encoder()

    def set_adresse_reseau(self, adresse_reseau):
        self.__logger.info("Adresse reseau : %s" % binascii.hexlify(adresse_reseau).decode('utf-8'))
        self.__adresse_reseau = adresse_reseau
        
    @property
    def adresse_reseau(self):
        return self.__adresse_reseau
    
    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        try:
            with self.__lock_reception:
                return self.__fifo_payload.pop(0)
        except IndexError:
            raise StopIteration()

    def wait_reception(self, timeout=None):
        """
        Attend qu'un evenement soit ajoute dans la FIFO
        :param timeout:
        :return: True si evenment set
        """
        self.__event_reception.wait(timeout)
        evenement_produit = self.__event_reception.is_set()
        self.__event_reception.clear()
        return evenement_produit


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
            pass
        elif type_env == 'int':
            self.__logger.setLevel(logging.DEBUG)
            logging.getLogger('mgraspberry').setLevel(logging.DEBUG)
        else:
            self.__logger.setLevel(logging.DEBUG)
            logging.getLogger('mgraspberry').setLevel(logging.DEBUG)

        self._callback_soumettre = None
        self.thread = None
        self.__configuration = None

        self.__path_configuration = Constantes.PATH_CONFIGURATION
        self.__reserve_dhcp = ReserveDHCP(path.join(self.__path_configuration, 'rf24dhcp.json'))
        self.__information_appareils_par_uuid = dict()

        self.__traitement_radio = RadioThread(self.__stop_event, type_env)

        self.__adresse_serveur = None
        self.__adresse_serveur = None

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
            self.__logger.info("Charge configuration:\n%s" % json.dumps(self.__configuration, indent=4))

            adresses = self.__configuration['adresses']
            
            adresse_serveur = binascii.unhexlify(adresses['serveur'].encode('utf8'))
            adresse_reseau = binascii.unhexlify(adresses['reseau'].encode('utf8'))

        except FileNotFoundError:
            self.__logger.info("Creation d'une nouvelle configuration pour le serveur")

            adresse_serveur = urandom(3)  # Generer 3 bytes pour l'adresse serveur receiving pipe
            adresse_reseau = urandom(4)   # Generer 4 bytes pour l'adresse du reseau
            
            configuration = {
                'adresses': {
                    'serveur': binascii.hexlify(adresse_serveur).decode('utf8'),
                    'reseau': binascii.hexlify(adresse_reseau).decode('utf8'),
                }
            }
            self.__logger.debug("Configuration: %s" % str(configuration))
            with open(path.join(self.__path_configuration, 'rf24server.json'), 'w') as fichier:
                json.dump(configuration, fichier)
            self.__configuration = configuration

        finally:
            self.__traitement_radio.set_adresse_serveur(adresse_serveur)
            self.__traitement_radio.set_adresse_reseau(adresse_reseau)

    # Starts thread and runs the process
    def start(self, callback_soumettre):
        self.__traitement_radio.start()
        self._callback_soumettre = callback_soumettre
        self.thread = Thread(name="RF24Server", target=self.run, daemon=True)
        self.thread.start()

    def __process_paquets(self):
        for payload in self.__traitement_radio:
            self.__logger.debug("Payload %s bytes\n%s" % (len(payload), binascii.hexlify(payload).decode('utf-8')))
            self.process_paquet_payload(payload)
                
    def __executer_cycle(self):
        # Traiter paquets dans FIFO
        self.__process_paquets()

    def run(self):
        self.__logger.info("RF24Server: thread started successfully")

        # Boucle principale d'execution
        while not self.__stop_event.is_set():
            try:
                self.__executer_cycle()
                # Throttle le service
                self.__traitement_radio.wait_reception(2.0)
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
        uuid_senseur = binascii.hexlify(paquet0.uuid).decode('utf-8')
        info_appareil = self.__information_appareils_par_uuid.get(uuid_senseur)
        message = AssembleurPaquets(paquet0, info_appareil)
        self.__assembleur_par_nodeId[node_id] = message

    def process_paquet_payload(self, payload):
        
        # Extraire premier bytes pour routing / traitement
        # Noter que pour les paquets cryptes, type_paquet n'est pas utilisable
        version, from_node_id, no_paquet, type_paquet = struct.unpack('BBHH', payload[0:6])
        
        if version == VERSION_PROTOCOLE:
            self.__logger.debug("Type paquet: %d" % type_paquet) 

            if no_paquet == 0:
                if type_paquet == TypesMessages.TYPE_PAQUET0:
                    # Paquet0
                    self.process_paquet0(from_node_id, payload)
                elif type_paquet == TypesMessages.TYPE_REQUETE_DHCP:
                    self.process_dhcp_request(payload)
            else:
                assembleur = self.__assembleur_par_nodeId.get(from_node_id)
                if assembleur is not None:
                    try:
                        complet = assembleur.recevoir(payload)
                        if complet:
                            try:
                                self._assembler_message(assembleur)
                            except ValueError as ve:
                                self.__logger.error("%s" % str(ve))
                            finally:
                                del self.__assembleur_par_nodeId[from_node_id]
                    except ProtocoleVersion9.ExceptionCipherNonDisponible as e:
                        self.__logger.warning("Cipher non disponible %s:" % str(e))
                else:
                    self.__logger.info("Message dropped, paquet 0 inconnu pour nodeId:%d" % from_node_id)
        else:
            self.__logger.warning("Message version non supportee : %d" % version)

    def _assembler_message(self, assembleur):
        message, paquet_ack = assembleur.assembler()
        # message_json = json.dumps(message, indent=2)
        # self.__logger.debug("Message complet: \n%s" % message_json)

        if assembleur.iv_confirme:
            # Conserver le nouveau IV pour l'appareil
            self.__ajouter_iv_appareil(assembleur.uuid_appareil, assembleur.iv)

        # Transmettre message recu a MQ
        if assembleur.type_transmission == TypesMessages.MSG_TYPE_LECTURES_COMBINEES:
            self.transmettre_ack(paquet_ack)
            self._callback_soumettre(message)
        elif assembleur.type_transmission == TypesMessages.MSG_TYPE_NOUVELLE_CLE:
            self.__logger.debug("Nouvelle cle : %s" % message)
            self.__ajouter_cle_appareil(assembleur.node_id, message)
        else:
            self.__logger.error("Type transmission inconnu : %s" % str(assembleur.type_transmission))

    def transmettre_ack(self, paquet_ack):
        self.__logger.debug("Transmettre ACK vers Id: %s" % str(paquet_ack.node_id))
        self.transmettre_paquets([paquet_ack], paquet_ack.node_id)

    def transmettre_response_dhcp(self, node_id_assigne, node_uuid):
        """
        Repond a une demande DHCP d'un appareil.
        """
        paquet = PaquetReponseDHCP(self.__traitement_radio.adresse_reseau, node_id_assigne, node_uuid)
        self.__logger.debug("Transmettre reponse DHCP vers: %s" % binascii.hexlify(node_uuid).decode('utf-8'))
        self.transmettre_paquets([paquet])

    def transmettre_paquets(self, paquets: list, node_id = None):
        """
        Transmet une sequence de paquets relies. Si un paquet echoue,
        le reste des paquets ne seront pas transmis.
        """
        for paquet in paquets:
            self.__traitement_radio.transmettre(paquet)
        

    # Close all connections and the radio
    def fermer(self):
        self.__stop_event.set()
        try:
            self.__radio.stopListening()
            self.__radio = None
        except Exception as e:
            self.__logger.warning("NRF24MeshServer: Error closing radio: %s" % str(e))

    def __ajouter_iv_appareil(self, uuid_senseur, iv):
        info_appareil = self.__information_appareils_par_uuid.get(uuid_senseur)
        self.__logger.debug("Nouveau IV pour appareil %s : %s" % (uuid_senseur, binascii.hexlify(iv)))
        if info_appareil is not None:
            info_appareil['iv'] = iv

    def __ajouter_cle_appareil(self, node_id, message):
        self.__logger.debug("Messages : %s"  % str(message))
        uuid_senseur = message['uuid_senseur']
        cle = message['cle_publique']
        self.__logger.debug("Recu cle publique appareil : %s" % binascii.hexlify(cle))
        
        # Generer nouvelle cle ed25519 pour identifier cle partagee
        appareil_side = donna25519.PublicKey(cle)
        serveur_side = donna25519.PrivateKey()
        shared_key = serveur_side.do_exchange(appareil_side)
        # self.__logger.debug("Cle shared %s : %s" % (uuid_senseur, binascii.hexlify(shared_key)))
        
        # Transmettre serveur side public
        serveur_side_public = bytes(serveur_side.get_public().public)
        self.__logger.debug("Cle publique serveur : %s" % binascii.hexlify(serveur_side_public))
        # self.__logger.debug("Cle privee serveur : %s" % binascii.hexlify(bytes(serveur_side)))
        
        paquets = [
            ProtocoleVersion9.PaquetReponseCleServeur1(node_id, serveur_side_public),
            ProtocoleVersion9.PaquetReponseCleServeur2(node_id, serveur_side_public),
        ]
        self.__logger.debug("Transmission paquet cle publique vers reponse nodeId:%d" % node_id)
        self.transmettre_paquets(paquets, node_id)
        
        info_appareil = self.__information_appareils_par_uuid.get(uuid_senseur)
        if info_appareil is None:
            info_appareil = dict()
            self.__information_appareils_par_uuid[uuid_senseur] = info_appareil
        info_appareil['cle_partagee'] = shared_key


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

