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