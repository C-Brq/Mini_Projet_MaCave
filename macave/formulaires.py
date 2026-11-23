# Conversion du texte des formulaires (ValueError si invalide)
from datetime import date

from macave.enums import TypeVin

# (valeur, libellé) pour les listes déroulantes
TYPES_DE_VIN = []
for un_type in TypeVin:
    TYPES_DE_VIN.append((un_type.value, un_type.libelle()))


def lire_entier(texte, nom):
    # "12" devient 12
    try:
        return int(texte.strip())
    except ValueError:
        raise ValueError(nom + " doit être un nombre entier.")


def lire_nombre(texte, nom):
    # Accepte la virgule ou le point
    try:
        return float(texte.strip().replace(",", "."))
    except ValueError:
        raise ValueError(nom + " doit être un nombre.")


def lire_date(texte, nom):
    # Format AAAA-MM-JJ d'un champ date
    try:
        return date.fromisoformat(texte.strip())
    except ValueError:
        raise ValueError(nom + " n'est pas une date valide.")
