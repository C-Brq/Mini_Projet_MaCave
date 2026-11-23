from macave.enums import TypeVin
from macave.validation import (LONGUEUR_MAXIMUM_ADRESSE, LONGUEUR_MAXIMUM_DESCRIPTION, nettoyer_texte,
                               verifier_entier_positif, verifier_longueur)


class Vin:
    # Référence du catalogue, pas un exemplaire. Moyenne : voir CatalogueService

    def __init__(self, domaine: str, nom: str, type, millesime: int, region: str,
                 description: str = "", photo_etiquette: str = "", id=None):
        if not isinstance(type, TypeVin):
            raise ValueError("Le type du vin doit être rouge, blanc, rosé ou effervescent.")
        verifier_entier_positif(millesime, "Le millésime")
        verifier_longueur(description, LONGUEUR_MAXIMUM_DESCRIPTION, "La description")
        verifier_longueur(photo_etiquette, LONGUEUR_MAXIMUM_ADRESSE, "L'adresse de la photo")
        self.id = id
        self.domaine = nettoyer_texte(domaine, "Le domaine")  # espaces en trop enlevés
        self.nom = nettoyer_texte(nom, "Le nom du vin")
        self.type = type  # un TypeVin
        self.millesime = millesime
        self.region = nettoyer_texte(region, "La région")
        # « | » sert de séparateur dans la clé d'identité
        if "|" in self.domaine + self.nom + self.region:
            raise ValueError("Le caractère | n'est pas autorisé dans le domaine, le nom ni la région.")
        self.description = description
        self.photo_etiquette = photo_etiquette

    def cle_identite(self) -> str:
        # Ex. : "château montelena|cabernet sauvignon|rouge|1967|californie"
        morceaux = [self.domaine, self.nom, self.type.value, str(self.millesime), self.region]
        return "|".join(morceaux).lower()

    def est_le_meme_vin_que(self, autre) -> bool:
        return self.cle_identite() == autre.cle_identite()
