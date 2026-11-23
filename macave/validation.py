# Contrôles de saisie (ValueError si refusé)

# SQLite plafonne à 2**63 : on limite bien plus bas
ENTIER_MAXIMUM = 1000000


def verifier_entier_positif(valeur, nom):
    # refuse aussi 2.5, "5" et True
    if type(valeur) is not int or valeur <= 0 or valeur > ENTIER_MAXIMUM:
        raise ValueError(nom + " doit être un entier strictement positif (1 000 000 au maximum).")


PRIX_MAXIMUM = 1000000


def verifier_prix(valeur):
    # refuse aussi nan et l'infini
    if type(valeur) not in (int, float) or not 0 <= valeur <= PRIX_MAXIMUM:
        raise ValueError("Le prix d'achat doit être un nombre compris entre 0 et 1 000 000.")


# Longueurs maximales des textes
LONGUEUR_MAXIMUM_NOM = 100           # domaine, nom du vin, région, nom d'une étagère
LONGUEUR_MAXIMUM_DESCRIPTION = 1000  # description d'un vin, commentaire d'une évaluation
LONGUEUR_MAXIMUM_ADRESSE = 500       # adresse web de la photo d'une étiquette


def nettoyer_texte(texte, nom):
    # Enlève les espaces en trop, refuse vide ou trop long
    if type(texte) is not str:
        raise ValueError(nom + " doit être un texte.")
    # "  Château   Montelena " devient "Château Montelena"
    texte = " ".join(texte.split())
    if texte == "":
        raise ValueError(nom + " ne peut pas être vide.")
    verifier_longueur(texte, LONGUEUR_MAXIMUM_NOM, nom)
    return texte


def verifier_longueur(texte, maximum, nom):
    # None (champ absent) est accepté
    if texte is not None and len(texte) > maximum:
        raise ValueError(nom + " ne peut pas dépasser " + str(maximum) + " caractères.")
