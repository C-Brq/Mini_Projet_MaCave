from macave.erreurs import IntrouvableError
from macave.vin_repository import VinRepository


class CatalogueService:
    # Catalogue commun et évaluations

    def __init__(self, connexion):
        self.connexion = connexion
        self.vins = VinRepository(connexion)

    def creer_vin(self, vin):
        # Renvoie (vin, cree) ; cree vaut False si le vin existait déjà
        with self.connexion:
            # verrou d'écriture : pas de doublon en cas d'accès simultanés
            self.connexion.execute("BEGIN IMMEDIATE")
            return self.vins.trouver_ou_creer(vin)

    def charger_vin(self, vin_id):
        vin = self.vins.trouver(vin_id)
        if vin is None:
            raise IntrouvableError("Vin introuvable.")
        return vin

    def lister_vins(self):
        return self.vins.lister()

    def moyennes_par_vin(self):
        # {id du vin: (moyenne, nombre d'évaluations)}
        return self.vins.moyennes_par_vin()

    def note_moyenne(self, vin_id):
        # (moyenne, nombre) ; moyenne à None sans évaluation
        return self.vins.note_moyenne(vin_id)

    def evaluations_du_vin(self, vin_id):
        return self.vins.evaluations_du_vin(vin_id)
