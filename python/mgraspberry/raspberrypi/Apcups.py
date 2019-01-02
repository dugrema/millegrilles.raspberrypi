# Module pour lire l'etat d'un UPS APC.
# coding=utf-8


import socket
from struct import pack
import re
import time
import datetime
from dateutil.parser import parse
import os
import errno
import logging


class ApcupsdCollector:
    """ Copie de https://github.com/python-diamond/Diamond/blob/master/src/collectors/apcupsd/apcupsd.py """

    def __init__(self):
        self._config = None
        self._dernier_evenement = None

        self._logger = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        self._config = {
            'path':     'apcupsd',
            'hostname': 'localhost',
            'port': 3551,
            'metrics': ['LINEV', 'LOADPCT', 'BCHARGE', 'TIMELEFT', 'BATTV',
                        'NUMXFERS', 'TONBATT', 'MAXLINEV', 'MINLINEV',
                        'OUTPUTV', 'ITEMP', 'LINEFREQ', 'CUMONBATT', ],
        }
        return self._config

    def get_data(self):
        # Get the data via TCP stream
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self._config['hostname'], int(self._config['port'])))

        # Packet is pad byte, size byte, and command
        s.send(pack('xb6s', 6, b'status'))

        # Ditch the header
        s.recv(1024)
        time.sleep(.25)
        data = s.recv(4096)

        # We're done. Close the socket
        s.close()
        return data

    def get_events(self):
        # Get the data via TCP stream
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self._config['hostname'], int(self._config['port'])))

        # Packet is pad byte, size byte, and command
        s.send(pack('xb6s', 6, b'events'))

        # Ditch the header
        time.sleep(.25)
        data = s.recv(4096)

        # We're done. Close the socket
        s.close()

        self._logger.debug("Events data: %s" % data)
        split_bytes = data.split(b'\n\x00')
        self._logger.debug("Split bytes events: %s" % str(split_bytes))

        regex_metric = re.compile('(.?)([0-9-: ]{25})\s{2}(.*)')
        contenu = []
        for event in split_bytes:
            matches = re.search(regex_metric, str(event))
            if matches:
                self._logger.debug("Commande: %s, Date: %s, Event: %s" % (matches.group(1), matches.group(2), matches.group(3)))
                date = parse(matches.group(2))
                contenu.append((matches.group(1), date, matches.group(3)))

        return contenu

    def ecouter_evenements(self):
        # Ouvrir un pipe utilise pour recevoir l'etat de APCUPSD
        pipe_fichier = '/home/mathieu/pipe'
        try:
            os.mkfifo(pipe_fichier)
        except OSError as oe:
            if oe.errno != errno.EEXIST:
                raise

        while True:
            with open(pipe_fichier) as pipe:
                while True:
                    line = pipe.read()
                    if len(line) == 0:
                        self._logger.debug("Ferme")
                        break
                    self._logger.debug("Contenu: %s" % str(line))

    def evenements(self, data):
        self._logger.debug("Events data: %s" % data)
        split_bytes = data.split(b'\n\x00')
        self._logger.debug("Split bytes events: %s" % str(split_bytes))

        regex_metric = re.compile('(.?)([0-9-: ]{25})\s{2}(.*)')
        contenu = []
        for event in split_bytes:
            matches = re.search(regex_metric, str(event))
            if matches:
                self._logger.debug("Commande: %s, Date: %s, Event: %s" % (matches.group(1), matches.group(2), matches.group(3)))
                date = parse(matches.group(2))
                contenu.append((matches.group(1), date, matches.group(3)))

        return contenu

    def collect(self):
        metrics = {}
        raw = {}

        data = self.get_data()

        data = data.split(b'\n\x00')
        self._logger.debug("Data : %s" % str(data))

        regex_metric = re.compile('([A-Z]*) +:(.*)')

        for d in data:
            # matches = re.search("([A-Z]+):(.*)$", d)
            matches = re.search(regex_metric, str(d))
            if matches:
                value = matches.group(2).strip()
                raw[matches.group(1)] = matches.group(2).strip()
                vmatch = re.search("([0-9.]+)", value)
                if not vmatch:
                    continue
                try:
                    value = float(vmatch.group(1))
                except ValueError:
                    continue
                metric_key = matches.group(1)
                self._logger.debug("Key: %s, Value: %s" % (metric_key, raw[metric_key]))
                metrics[matches.group(1)] = value

        # Convertir les valeurs numeriques
        contenu = dict()
        for metric in self._config['metrics']:
            if metric not in metrics:
                continue

            value = metrics[metric]
            if metric in ['TONBATT', 'CUMONBATT', 'NUMXFERS', 'LINEV', 'LOADPCT', 'BCHARGE']:
                contenu[metric] = value
            elif metric in ['TIMELEFT']:
                contenu[metric] = value * 60.0  # Convertir minutes en secondes
            else:
                contenu[metric] = raw[metric]

        self._logger.debug("Metriques: %s" % str(contenu))

        return contenu
