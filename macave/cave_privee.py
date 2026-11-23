from datetime import date

from macave.bouteille import Bouteille
from macave.etagere import Etagere
from macave.validation import nettoyer_texte, verifier_entier_positif


class CavePrivee:
    def __init__(self, proprietaire, id=None):
        self.id = id
        self.proprietaire = proprietaire  # un Utilisateur
        self.etageres = []
        self.bouteilles = []  # en stock et archivées

    def appartient_a(self, utilisateur) -> bool:
        if self.proprietaire is utilisateur:
            return True
        # même compte rechargé : on compare les id
        return utilisateur.id is not None and self.proprietaire.id == utilisateur.id

    def creer_etagere(self, nom: str, capacite_max: int) -> Etagere:
        etagere = Etagere(nom, capacite_max)  # vérifie le nom et la capacité
        self._verifier_nom_libre(etagere.nom, None)
        self.etageres.append(etagere)
        return etagere

    def modifier_etagere(self, etagere: Etagere, nom: str, capacite_max: int) -> None:
        # Tout ou rien : nom et capacité
        nouveau_nom = nettoyer_texte(nom, "Le nom de l'étagère")
        self._verifier_nom_libre(nouveau_nom, etagere)
        etagere.modifier_capacite(capacite_max)  # refuse si capacité < occupation
        etagere.nom = nouveau_nom                # nom changé en dernier

    def _verifier_nom_libre(self, nom: str, etagere_ignoree) -> None:
        # Noms uniques sans tenir compte de la casse (R2)
        for autre in self.etageres:
            if autre is not etagere_ignoree and autre.nom.lower() == nom.lower():
                raise ValueError("Une étagère porte déjà ce nom dans cette cave.")

    def supprimer_etagere(self, etagere: Etagere) -> None:
        if not etagere.est_vide():
            raise ValueError("Impossible de supprimer une étagère qui n'est pas vide.")
        self.etageres.remove(etagere)

    def ajouter_bouteilles(self, vin, etagere: Etagere, quantite: int, prix_achat,
                           date_ajout: date = None) -> list:
        # Tout ou rien : on vérifie avant de créer
        verifier_entier_positif(quantite, "La quantité")
        if etagere not in self.etageres:
            raise ValueError("Cette étagère n'appartient pas à cette cave.")
        if date_ajout is not None:
            if not isinstance(date_ajout, date):
                raise ValueError("La date d'ajout n'est pas valide.")
            if date_ajout > date.today():
                raise ValueError("La date d'ajout ne peut pas être dans le futur.")
        if quantite > etagere.places_libres():
            raise ValueError("Capacité de l'étagère dépassée.")

        nouvelles = []
        for _ in range(quantite):
            nouvelles.append(Bouteille(vin, self, prix_achat, date_ajout))
        etagere.accueillir(nouvelles)
        self.bouteilles.extend(nouvelles)
        return nouvelles

    def bouteilles_en_stock(self) -> list:
        return [b for b in self.bouteilles if b.est_en_stock()]

    def historique(self) -> list:
        return [b for b in self.bouteilles if not b.est_en_stock()]

    def nb_bouteilles(self) -> int:
        return len(self.bouteilles_en_stock())

    def nb_references(self) -> int:
        # Nombre de vins différents en stock
        # un set compte chaque vin une seule fois
        cles = {b.vin.cle_identite() for b in self.bouteilles_en_stock()}
        return len(cles)

    def capacite_totale(self) -> int:
        return sum(e.capacite_max for e in self.etageres)

    def occupation_globale(self):
        # None s'il n'y a aucune étagère
        capacite = self.capacite_totale()
        if capacite == 0:
            return None
        return self.nb_bouteilles() / capacite

    def valeur_stock(self) -> float:
        total = 0
        for bouteille in self.bouteilles_en_stock():
            total += bouteille.prix_achat
        # arrondi au centime (0.1 + 0.2 = 0.30000000000000004)
        return round(total, 2)
