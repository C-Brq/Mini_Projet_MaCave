from datetime import datetime

from macave.validation import LONGUEUR_MAXIMUM_DESCRIPTION, verifier_longueur


def verifier_note(note) -> None:
    if not 0 <= note <= 20:
        raise ValueError("La note doit être comprise entre 0 et 20.")


class Evaluation:
    def __init__(self, auteur, vin, bouteille, note: float, commentaire: str = None, id=None):
        verifier_note(note)
        verifier_longueur(commentaire, LONGUEUR_MAXIMUM_DESCRIPTION, "Le commentaire")
        self.id = id
        self.auteur = auteur  # un Utilisateur
        self.vin = vin
        self.bouteille = bouteille
        self.note = note
        self.commentaire = commentaire
        self.date = datetime.now()

    def est_modifiable_par(self, utilisateur) -> bool:
        if self.auteur is utilisateur:
            return True
        # même compte rechargé : on compare les id
        # deux id None ne sont pas la même personne
        return utilisateur.id is not None and self.auteur.id == utilisateur.id

    def modifier(self, auteur, note: float, commentaire: str = None) -> None:
        if not self.est_modifiable_par(auteur):
            raise PermissionError("Une évaluation n'est modifiable que par son auteur.")
        verifier_note(note)
        verifier_longueur(commentaire, LONGUEUR_MAXIMUM_DESCRIPTION, "Le commentaire")
        self.note = note
        self.commentaire = commentaire
