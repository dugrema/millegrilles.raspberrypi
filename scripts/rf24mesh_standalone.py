import logging
import json

from millegrilles import Constantes
from mgraspberry.raspberrypi.RF24Mesh import NRF24MeshServer

logging.basicConfig(format=Constantes.LOGGING_FORMAT)

logger = logging.getLogger('__main__')
logger.setLevel(logging.DEBUG)


def print_message(message: dict):
    json_message = json.dumps(message, indent=2)
    logger.info("Message recu: \n%s" % json_message)


server = NRF24MeshServer()
server.start(print_message)


