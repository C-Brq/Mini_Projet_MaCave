# Recherche, filtre et tri, sans Flask ni base
from macave.cave_privee import CavePrivee
from macave.enums import TypeVin
from macave.recherche import lignes_de_bouteilles, rechercher, sans_accents, valeur_de_tri
from macave.utilisateur import Utilisateur
from macave.vin import Vin


def noms(lignes):
    # Noms des vins, dans l'ordre
    return [ligne["vin"].nom for ligne in lignes]


def preparer_stock():
    # Quatre vins, une bouteille chacun ; le rosé n'a pas de note
    cave = CavePrivee(Utilisateur("alice", "alice@example.fr", "motdepasse1"))
    etagere = cave.creer_etagere("E1", 20)
    vins = {
        "cabernet": Vin("Château Montelena", "Cabernet Sauvignon", TypeVin.ROUGE, 1967, "Californie"),
        "chardonnay": Vin("Domaine de l'Élysée", "Chardonnay", TypeVin.BLANC, 2015, "Bourgogne"),
        "rose": Vin("Domaine Zéta", "Rosé d'été", TypeVin.ROSE, 2020, "Provence"),
        "cremant": Vin("Maison Brut", "Crémant", TypeVin.EFFERVESCENT, 2018, "Alsace"),
    }
    prix = {"cabernet": 50, "chardonnay": 30, "rose": 12.5, "cremant": 25}
    for cle, vin in vins.items():
        vin.id = len(cave.bouteilles) + 1  # un id par vin, comme s'ils venaient de la base
        cave.ajouter_bouteilles(vin, etagere, 1, prix[cle])
    moyennes = {vins["cabernet"].id: (16.0, 3), vins["chardonnay"].id: (12.0, 1),
                vins["cremant"].id: (17.0, 2)}
    return lignes_de_bouteilles(cave.bouteilles_en_stock(), moyennes), cave


# Accents et casse

def test_sans_accents_enleve_les_accents_et_met_en_minuscules():
    assert sans_accents("Château ÉLYSÉE") == "chateau elysee"
    assert sans_accents("Rosé d'été") == "rose d'ete"
    assert sans_accents("Cabernet") == "cabernet"


# Recherche

def test_sans_recherche_toutes_les_lignes_sont_gardees_dans_l_ordre_d_origine():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes)) == ["Cabernet Sauvignon", "Chardonnay", "Rosé d'été", "Crémant"]


def test_recherche_par_nom():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, "cabernet")) == ["Cabernet Sauvignon"]


def test_recherche_par_domaine():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, "montelena")) == ["Cabernet Sauvignon"]
    assert noms(rechercher(lignes, "domaine")) == ["Chardonnay", "Rosé d'été"]


def test_recherche_sans_tenir_compte_des_accents_ni_de_la_casse():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, "CHATEAU")) == ["Cabernet Sauvignon"]   # « Château »
    assert noms(rechercher(lignes, "elysee")) == ["Chardonnay"]            # « Élysée »
    assert noms(rechercher(lignes, "  rosé ")) == ["Rosé d'été"]           # avec des espaces autour
    assert noms(rechercher(lignes, "cremant")) == ["Crémant"]


def test_recherche_sans_resultat():
    lignes, _ = preparer_stock()
    assert rechercher(lignes, "inexistant") == []


def test_filtre_par_type():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, type_vin="blanc")) == ["Chardonnay"]
    assert noms(rechercher(lignes, type_vin="rose")) == ["Rosé d'été"]
    assert noms(rechercher(lignes, type_vin="effervescent")) == ["Crémant"]
    assert rechercher(lignes, type_vin="n'importe quoi") == []


def test_recherche_et_filtre_se_combinent():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, "domaine", type_vin="blanc")) == ["Chardonnay"]
    assert rechercher(lignes, "montelena", type_vin="blanc") == []


# Tri dans les deux sens

def test_tri_par_domaine_dans_les_deux_sens():
    lignes, _ = preparer_stock()
    # tri sans tenir compte des accents ni de la casse
    assert noms(rechercher(lignes, tri="domaine")) == ["Cabernet Sauvignon", "Chardonnay", "Rosé d'été", "Crémant"]
    assert noms(rechercher(lignes, tri="domaine", sens="desc")) == ["Crémant", "Rosé d'été", "Chardonnay", "Cabernet Sauvignon"]


def test_tri_par_nom_dans_les_deux_sens():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, tri="nom")) == ["Cabernet Sauvignon", "Chardonnay", "Crémant", "Rosé d'été"]
    assert noms(rechercher(lignes, tri="nom", sens="desc")) == ["Rosé d'été", "Crémant", "Chardonnay", "Cabernet Sauvignon"]


def test_tri_par_type_dans_les_deux_sens():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, tri="type")) == ["Chardonnay", "Crémant", "Rosé d'été", "Cabernet Sauvignon"]
    assert noms(rechercher(lignes, tri="type", sens="desc")) == ["Cabernet Sauvignon", "Rosé d'été", "Crémant", "Chardonnay"]


def test_tri_par_millesime_dans_les_deux_sens():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, tri="millesime")) == ["Cabernet Sauvignon", "Chardonnay", "Crémant", "Rosé d'été"]
    assert noms(rechercher(lignes, tri="millesime", sens="desc")) == ["Rosé d'été", "Crémant", "Chardonnay", "Cabernet Sauvignon"]


def test_tri_par_region_dans_les_deux_sens():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, tri="region")) == ["Crémant", "Chardonnay", "Cabernet Sauvignon", "Rosé d'été"]
    assert noms(rechercher(lignes, tri="region", sens="desc")) == ["Rosé d'été", "Cabernet Sauvignon", "Chardonnay", "Crémant"]


def test_tri_par_prix_dans_les_deux_sens():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, tri="prix")) == ["Rosé d'été", "Crémant", "Chardonnay", "Cabernet Sauvignon"]
    assert noms(rechercher(lignes, tri="prix", sens="desc")) == ["Cabernet Sauvignon", "Chardonnay", "Crémant", "Rosé d'été"]


def test_tri_par_note_communautaire_dans_les_deux_sens():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, tri="note"))[:3] == ["Chardonnay", "Cabernet Sauvignon", "Crémant"]
    assert noms(rechercher(lignes, tri="note", sens="desc"))[:3] == ["Crémant", "Cabernet Sauvignon", "Chardonnay"]


# Valeurs absentes

def test_un_vin_sans_note_est_toujours_en_dernier_quel_que_soit_le_sens():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, tri="note"))[-1] == "Rosé d'été"
    assert noms(rechercher(lignes, tri="note", sens="desc"))[-1] == "Rosé d'été"


def test_le_tri_par_note_ne_confond_pas_une_absence_de_note_avec_zero():
    lignes, _ = preparer_stock()
    # si l'absence valait 0, le rosé serait premier
    assert noms(rechercher(lignes, tri="note"))[0] == "Chardonnay"


def test_tri_par_ma_note_et_par_date_dans_l_historique():
    lignes, cave = preparer_stock()
    cave.bouteilles[0].archiver(10)                  # Cabernet
    cave.bouteilles[1].archiver(18)                  # Chardonnay
    cave.bouteilles[3].archiver(14)                  # Crémant
    historique = lignes_de_bouteilles(cave.historique(), {})
    assert noms(rechercher(historique, tri="ma_note")) == ["Cabernet Sauvignon", "Crémant", "Chardonnay"]
    assert noms(rechercher(historique, tri="ma_note", sens="desc")) == ["Chardonnay", "Crémant", "Cabernet Sauvignon"]
    # même date : ordre d'origine conservé
    assert noms(rechercher(historique, tri="date_sortie")) == ["Cabernet Sauvignon", "Chardonnay", "Crémant"]


def test_ma_note_et_date_de_sortie_sont_absentes_pour_une_bouteille_encore_en_stock():
    lignes, _ = preparer_stock()   # en stock : ni évaluation ni date de sortie
    assert noms(rechercher(lignes, tri="ma_note")) == noms(lignes)
    assert noms(rechercher(lignes, tri="date_sortie", sens="desc")) == noms(lignes)


def test_la_valeur_de_tri_d_un_critere_inconnu_est_absente():
    lignes, _ = preparer_stock()
    assert valeur_de_tri(lignes[0], "n_importe_quoi") is None


def test_le_prix_n_existe_pas_dans_le_catalogue_les_lignes_restent_dans_l_ordre():
    # catalogue sans bouteille : le tri par prix ne change rien
    lignes, _ = preparer_stock()
    catalogue = []
    for ligne in lignes:
        catalogue.append({"vin": ligne["vin"], "moyenne": ligne["moyenne"], "nb_evaluations": ligne["nb_evaluations"]})
    assert noms(rechercher(catalogue, tri="prix")) == noms(catalogue)


# Réglages invalides

def test_un_critere_de_tri_inconnu_est_ignore():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, tri="'; DROP TABLE vins; --")) == noms(lignes)


def test_un_sens_inconnu_donne_un_tri_croissant():
    lignes, _ = preparer_stock()
    assert noms(rechercher(lignes, tri="prix", sens="n'importe quoi")) == noms(rechercher(lignes, tri="prix"))
