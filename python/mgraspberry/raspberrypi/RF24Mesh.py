import RF24
import RF24Network
import RF24Mesh

from threading import Thread, Event

import binascii
import json
import time
import logging

from mgraspberry.raspberrypi.ProtocoleVersion7 import AssembleurPaquets, Paquet0, PaquetDemandeDHCP, PaquetReponseDHCP


class NRF24MeshServer:

    def __init__(self):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.__stop_event = Event()
        self.reception_par_nodeId = dict()
        self.__assembleur_par_nodeId = dict()
        self.__reserve_dhcp = ReserveDHCP()

        self.irq_gpio_pin = None

        self.__radio = None
        self.__network = None
        self.__mesh = None

        self._callback_soumettre = None

        self.thread = None

    def open_radio(self):
        self.__radio = RF24.RF24(RF24.RPI_V2_GPIO_P1_22, RF24.BCM2835_SPI_CS0, RF24.BCM2835_SPI_SPEED_8MHZ)
        self.__network = RF24Network.RF24Network(self.__radio)
        self.__mesh = RF24Mesh.RF24Mesh(self.__radio, self.__network)

        self.__mesh.setNodeID(0)
        self.__mesh.begin(62)

        self.radio.setPALevel(RF24.RF24_PA_HIGH)  # Power Amplifier
        self.radio.printDetails()

    # Starts thread and runs the process
    def start(self, callback_soumettre):
        self.open_radio()
        self._callback_soumettre = callback_soumettre
        self.thread = Thread(target=self.run)
        self.thread.start()
        self.__logger.info("HubNRF24L: nRF24L thread started successfully")

    def run(self):

        # Boucle principale d'execution
        while not self.__stop_event.is_set():

            try:
                self.__mesh.update()
                self.__mesh.DHCP()

                while self.__network.available():

                    try:
                        header, payload = self.__network.peek(8)
                        taille_buffer = 24
                        header_type = chr(header.type)
                        if header_type == '2':
                            taille_buffer = 48
                        header, payload = self.__network.read(taille_buffer)
                        self.__logger.debug("Payload %s bytes\n%s" % (len(payload), binascii.hexlify(payload).decode('utf-8')))

                        if header_type in ['2', 'p']:
                            self.process_paquet_payload(header, payload)
                        elif header_type == 'P':
                            self.process_paquet0(header, payload)
                        elif header_type == 'D':
                            self.process_dhcp_request(header, payload)

                    except Exception as e:
                        self.__logger.exception("HubNRF24L: Error processing radio message")
                        self.__stop_event.wait(5)  # Attendre 5 secondes avant de poursuivre

                self.__stop_event.wait(0.005)  # Throttle le service

            except Exception as e:
                self.__logger.exception("HubNRF24L: Error processing update ou DHCP")
                self.__stop_event.wait(5)  # Attendre 5 secondes avant de poursuivre

    def process_dhcp_request(self, header, payload):
        fromNodeId = self.__mesh.getNodeID(header.from_node)
        paquet = PaquetDemandeDHCP(header, payload, fromNodeId)

        # On utilise le node id actuel (pour repondre) comme suggestion
        node_id_suggere = paquet.node_id_reponse
        node_id_reserve = self.__reserve_dhcp.reserver(paquet.uuid, node_id_suggere)
        self.__logger.debug("Transmission DHCP reponse nodeId: %d (reponse vers %d)" % (node_id_reserve, node_id_suggere))

        # On transmet la reponse
        self.transmettre_response_dhcp(node_id_suggere, node_id_reserve)

    def process_paquet0(self, header, payload):
        fromNodeId = self.__mesh.getNodeID(header.from_node)
        paquet0 = Paquet0(header, payload)
        message = AssembleurPaquets(paquet0)
        self.__assembleur_par_nodeId[fromNodeId] = message
        self.__logger.debug("Paquet0 from node ID: %s, %s" % (str(fromNodeId), str(paquet0)))
        self.__logger.debug("Paquet0 bin: %s" % binascii.hexlify(payload))

    def process_paquet_payload(self, header, payload):
        fromNodeId = self.__mesh.getNodeID(header.from_node)
        assembleur = self.__assembleur_par_nodeId.get(fromNodeId)
        if assembleur is not None:
            complet = assembleur.recevoir(header, payload)
            if complet:
                message = assembleur.assembler()
                message = json.dumps(message, indent=2)
                self.__logger.debug("Message complet: \n%s" % message)

                # Transmettre message recu a MQ
                self._callback_soumettre(message)

                del self.__assembleur_par_nodeId[fromNodeId]
        else:
            self.__logger.info("Message dropped, paquet 0 inconnu pour nodeId:%d" % fromNodeId)

    def transmettre_response_dhcp(self, node_id_reponse, node_id_assigne):

        paquet = PaquetReponseDHCP(node_id_assigne)
        message = paquet.encoder()
        for essai in range(0, 4):
            reponse = self.__mesh.write(message, ord('d'), node_id_reponse)
            if not reponse:
                self.__logger.warning("Erreur transmission reponse %s" % str(reponse))
                self.__mesh.update()
                time.sleep(0.4)
            else:
                break

    # Close all connections and the radio
    def fermer(self):
        self.__stop_event.set()
        try:
            self.radio.stopListening()
            self.radio = None
        except Exception as e:
            self.__logger.warning("HubNRF24L: Error closing radio: %s" % str(e))


class ReserveDHCP:

    def __init__(self):
        self.__node_id_by_uuid = dict()
        self._next_node_id = 2

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

        return node_id

    def _identifier_nouvelle_adresse(self):

        node_id_list = self.__node_id_by_uuid.values()
        for node_id in range(2, 250):
            if node_id not in node_id_list:
                return node_id

        return None