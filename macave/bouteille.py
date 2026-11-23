from datetime import date

from macave.enums import StatutBouteille
from macave.evaluation import Evaluation
from macave.validation import verifier_prix


class Bouteille:
    # Exemplaire physique d'un vin

    def __init__(self, vin, cave, prix_achat, date_ajout: date = None, id=None):
        verifier_prix(prix_achat)
        self.id = id
        self.vin = vin
        self.cave = cave
        self.prix_achat = prix_achat
        self.date_ajout = date_ajout or date.today()
        self.statut = StatutBouteille.EN_STOCK
        self.date_sortie = None
        self.etagere = None     # None si pas rangée ou archivée
        self.evaluation = None  # remplie à l'archivage

    def est_en_stock(self) -> bool:
        return self.statut == StatutBouteille.EN_STOCK

    def modifier_infos(self, prix_achat, date_ajout: date) -> None:
        # Seuls le prix et la date d'ajout sont modifiables
        if not self.est_en_stock():
            raise ValueError("Une bouteille archivée ne peut plus être modifiée.")
        verifier_prix(prix_achat)
        if not isinstance(date_ajout, date):
            raise ValueError("La date d'ajout n'est pas valide.")
        if date_ajout > date.today():
            raise ValueError("La date d'ajout ne peut pas être dans le futur.")
        # on modifie seulement si tout est valide
        self.prix_achat = prix_achat
        self.date_ajout = date_ajout

    def deplacer_vers(self, destination) -> None:
        if not self.est_en_stock():
            raise ValueError("Une bouteille archivée ne peut pas être déplacée.")
        if destination not in self.cave.etageres:
            raise ValueError("L'étagère de destination n'appartient pas à cette cave.")
        ancienne = self.etagere
        if destination is ancienne:
            return
        destination.accueillir([self])  # refuse si la destination est pleine
        if ancienne is not None:
            ancienne.retirer(self)

    def retirer(self) -> None:
        # Retrait définitif de la cave
        if not self.est_en_stock():
            raise ValueError("Une bouteille archivée ne peut pas être retirée.")
        if self.etagere is not None:
            self.etagere.retirer(self)
        self.cave.bouteilles.remove(self)

    def archiver(self, note: float, commentaire: str = None, date_sortie: date = None) -> Evaluation:
        # Archive après dégustation et renvoie l'évaluation
        if not self.est_en_stock():
            raise ValueError("Cette bouteille est déjà archivée.")
        if date_sortie is None:
            date_sortie = date.today()
        if not isinstance(date_sortie, date):
            raise ValueError("La date de sortie n'est pas valide.")
        if date_sortie < self.date_ajout:
            raise ValueError("La date de sortie ne peut pas être avant la date d'ajout de la bouteille.")
        if date_sortie > date.today():
            raise ValueError("La date de sortie ne peut pas être dans le futur.")
        # l'évaluation vérifie la note avant tout changement
        evaluation = Evaluation(self.cave.proprietaire, self.vin, self, note, commentaire)
        if self.etagere is not None:
            self.etagere.retirer(self)
        self.statut = StatutBouteille.ARCHIVEE
        self.date_sortie = date_sortie
        self.evaluation = evaluation
        return evaluation
