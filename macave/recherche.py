# Recherche, filtre et tri en Python ; valeurs absentes toujours en dernier
import unicodedata

# Critères de tri : (valeur dans l'URL, libellé)
TRIS_STOCK = [
    ("domaine", "Domaine"), ("nom", "Nom"), ("type", "Type"), ("millesime", "Millésime"),
    ("region", "Région"), ("prix", "Prix d'achat"), ("note", "Note communautaire"),
]
TRIS_CATALOGUE = [
    ("domaine", "Domaine"), ("nom", "Nom"), ("type", "Type"), ("millesime", "Millésime"),
    ("region", "Région"), ("note", "Note communautaire"),
]
TRIS_HISTORIQUE = [
    ("date_sortie", "Date de dégustation"), ("ma_note", "Ma note"), ("domaine", "Domaine"),
    ("nom", "Nom"), ("millesime", "Millésime"), ("note", "Note communautaire"),
]
SENS = [("asc", "Croissant"), ("desc", "Décroissant")]


def sans_accents(texte: str) -> str:
    # Minuscules sans accents : « Château » devient « chateau »
    decompose = unicodedata.normalize("NFD", texte)
    resultat = ""
    for caractere in decompose:
        if not unicodedata.combining(caractere):
            resultat += caractere
    return resultat.lower()


def lignes_de_bouteilles(bouteilles: list, moyennes: dict) -> list:
    # moyennes : {id du vin: (moyenne, nombre)}
    lignes = []
    for bouteille in bouteilles:
        moyenne, nb_evaluations = moyennes.get(bouteille.vin.id, (None, 0))
        lignes.append({"vin": bouteille.vin, "bouteille": bouteille,
                       "moyenne": moyenne, "nb_evaluations": nb_evaluations})
    return lignes


def valeur_de_tri(ligne: dict, tri: str):
    # None si la valeur est absente
    vin = ligne["vin"]
    bouteille = ligne.get("bouteille")  # None dans le catalogue

    if tri == "domaine":
        return sans_accents(vin.domaine)
    if tri == "nom":
        return sans_accents(vin.nom)
    if tri == "type":
        return vin.type.value
    if tri == "millesime":
        return vin.millesime
    if tri == "region":
        return sans_accents(vin.region)
    if tri == "note":
        return ligne["moyenne"]

    # critères propres à une bouteille
    if bouteille is None:
        return None
    if tri == "prix":
        return bouteille.prix_achat
    if tri == "date_sortie":
        return bouteille.date_sortie
    if tri == "ma_note":
        if bouteille.evaluation is None:
            return None
        return bouteille.evaluation.note
    return None  # critère inconnu


def premier_element(paire):
    # Clé de tri : la valeur de la paire
    return paire[0]


def trier(lignes: list, tri: str, sens: str) -> list:
    # sens = "desc" pour décroissant
    avec_valeur = []   # des paires (valeur, ligne)
    sans_valeur = []   # valeurs absentes, mises à la fin
    for ligne in lignes:
        valeur = valeur_de_tri(ligne, tri)
        if valeur is None:
            sans_valeur.append(ligne)
        else:
            avec_valeur.append((valeur, ligne))

    # on ne compare que les valeurs
    avec_valeur.sort(key=premier_element, reverse=(sens == "desc"))

    resultat = []
    for valeur, ligne in avec_valeur:
        resultat.append(ligne)
    return resultat + sans_valeur


def rechercher(lignes: list, recherche: str = "", type_vin: str = "", tri: str = "", sens: str = "asc") -> list:
    # Filtre par texte et type, puis trie (critère inconnu : ordre d'origine)
    terme = sans_accents(recherche.strip())

    gardees = []
    for ligne in lignes:
        vin = ligne["vin"]
        if terme != "":
            dans_le_nom = terme in sans_accents(vin.nom)
            dans_le_domaine = terme in sans_accents(vin.domaine)
            if not dans_le_nom and not dans_le_domaine:
                continue
        if type_vin != "" and vin.type.value != type_vin:
            continue
        gardees.append(ligne)

    criteres_connus = ["domaine", "nom", "type", "millesime", "region", "note", "prix",
                       "date_sortie", "ma_note"]
    if tri in criteres_connus:
        gardees = trier(gardees, tri, sens)
    return gardees
