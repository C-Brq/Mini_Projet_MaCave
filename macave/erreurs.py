class MaCaveError(Exception):
    # Erreur métier, affichable telle quelle
    pass


class DonneesInvalidesError(MaCaveError):
    # erreurs : {champ: message}

    def __init__(self, erreurs: dict):
        super().__init__("; ".join(erreurs.values()))
        self.erreurs = erreurs


class AuthentificationError(MaCaveError):
    pass


class IntrouvableError(MaCaveError):
    # Absent ou à un autre : même erreur, pour ne rien révéler
    pass
