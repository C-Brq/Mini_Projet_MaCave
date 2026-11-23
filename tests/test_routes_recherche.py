# Recherche, tri, historique et tableau de bord, par les pages
import pytest

from tests.aides import (ajouter_bouteilles, cave_de, client_connecte, creer_etagere, creer_vin_complet,
                         id_etagere, page)


@pytest.fixture
def alice(app):
    return client_connecte(app, "alice")


@pytest.fixture
def bob(app):
    return client_connecte(app, "bob")


def apparait_avant(contenu, premier, second):
    # Vrai si premier apparaît avant second
    return contenu.index(premier) < contenu.index(second)


def alice_avec_trois_vins(app, alice):
    # Alice : une étagère et trois vins faciles à repérer
    creer_etagere(alice, "E1", "20")
    etagere = id_etagere(app, "alice", "E1")
    ids = {}
    ids["zinfandel"] = creer_vin_complet(alice, "Alpha Domaine", "Zinfandel", "rouge", "2000", "Napa")
    ids["merlot"] = creer_vin_complet(alice, "Beta Domaine", "Merlot", "rouge", "2010", "Bordeaux")
    ids["albarino"] = creer_vin_complet(alice, "Gamma Domaine", "Albarino", "blanc", "2020", "Galice")
    ajouter_bouteilles(alice, ids["zinfandel"], etagere, 1, "30")
    ajouter_bouteilles(alice, ids["merlot"], etagere, 1, "10")
    ajouter_bouteilles(alice, ids["albarino"], etagere, 1, "20")
    return ids


def archiver(client, bouteille_id, note):
    client.post(f"/bouteilles/{bouteille_id}/archiver", data={"note": note})


def id_bouteille_du_vin(app, nom_du_vin):
    for bouteille in cave_de(app, "alice").bouteilles:
        if bouteille.vin.nom == nom_du_vin:
            return bouteille.id


# Stock : recherche et filtre

def test_le_stock_affiche_toutes_les_bouteilles_sans_recherche(app, alice):
    alice_avec_trois_vins(app, alice)
    contenu = page(alice.get("/bouteilles"))
    assert "Zinfandel" in contenu and "Merlot" in contenu and "Albarino" in contenu


def test_recherche_par_nom_dans_le_stock(app, alice):
    alice_avec_trois_vins(app, alice)
    contenu = page(alice.get("/bouteilles?q=merlot"))
    assert "Merlot" in contenu and "Zinfandel" not in contenu and "Albarino" not in contenu


def test_recherche_par_domaine_dans_le_stock(app, alice):
    alice_avec_trois_vins(app, alice)
    contenu = page(alice.get("/bouteilles?q=gamma"))
    assert "Albarino" in contenu and "Merlot" not in contenu


def test_filtre_par_type_dans_le_stock(app, alice):
    alice_avec_trois_vins(app, alice)
    contenu = page(alice.get("/bouteilles?type=blanc"))
    assert "Albarino" in contenu and "Merlot" not in contenu and "Zinfandel" not in contenu


def test_recherche_sans_resultat_affiche_un_message(app, alice):
    alice_avec_trois_vins(app, alice)
    assert "Aucune bouteille ne correspond" in page(alice.get("/bouteilles?q=introuvable"))


def test_la_recherche_ne_porte_que_sur_son_propre_stock(app, alice, bob):
    alice_avec_trois_vins(app, alice)
    assert "Merlot" not in page(bob.get("/bouteilles?q=merlot"))


# Stock : tri

def test_tri_du_stock_par_prix_dans_les_deux_sens(app, alice):
    alice_avec_trois_vins(app, alice)
    croissant = page(alice.get("/bouteilles?tri=prix&sens=asc"))
    assert apparait_avant(croissant, "Merlot", "Albarino") and apparait_avant(croissant, "Albarino", "Zinfandel")
    decroissant = page(alice.get("/bouteilles?tri=prix&sens=desc"))
    assert apparait_avant(decroissant, "Zinfandel", "Albarino") and apparait_avant(decroissant, "Albarino", "Merlot")


def test_tri_du_stock_par_nom_et_par_millesime(app, alice):
    alice_avec_trois_vins(app, alice)
    par_nom = page(alice.get("/bouteilles?tri=nom&sens=asc"))
    assert apparait_avant(par_nom, "Albarino", "Merlot") and apparait_avant(par_nom, "Merlot", "Zinfandel")
    par_millesime = page(alice.get("/bouteilles?tri=millesime&sens=desc"))
    assert apparait_avant(par_millesime, "Albarino", "Merlot") and apparait_avant(par_millesime, "Merlot", "Zinfandel")


def test_tri_du_stock_par_note_communautaire_avec_les_vins_sans_note_a_la_fin(app, alice, bob):
    ids = alice_avec_trois_vins(app, alice)
    # Bob note deux vins, Albarino reste sans note
    creer_etagere(bob, "B1", "10")
    for nom in ("zinfandel", "merlot"):
        ajouter_bouteilles(bob, ids[nom], id_etagere(app, "bob", "B1"), 1, "5")
    for bouteille in cave_de(app, "bob").bouteilles:
        if bouteille.vin.nom == "Zinfandel":
            archiver(bob, bouteille.id, "18")
        else:
            archiver(bob, bouteille.id, "12")

    croissant = page(alice.get("/bouteilles?tri=note&sens=asc"))
    assert apparait_avant(croissant, "Merlot", "Zinfandel") and apparait_avant(croissant, "Zinfandel", "Albarino")
    decroissant = page(alice.get("/bouteilles?tri=note&sens=desc"))
    assert apparait_avant(decroissant, "Zinfandel", "Merlot") and apparait_avant(decroissant, "Merlot", "Albarino")


def test_reglages_invalides_ne_font_pas_planter_la_page(app, alice):
    alice_avec_trois_vins(app, alice)
    adresse = "/bouteilles?tri=%27%3B%20DROP%20TABLE%20vins%3B--&sens=n_importe_quoi&type=%3Cscript%3E"
    reponse = alice.get(adresse)
    assert reponse.status_code == 200
    assert cave_de(app, "alice").nb_bouteilles() == 3


def test_le_texte_cherche_est_echappe_dans_la_page(app, alice):
    alice_avec_trois_vins(app, alice)
    contenu = page(alice.get("/bouteilles?q=<script>alert(1)</script>"))
    assert "<script>alert(1)</script>" not in contenu


# Catalogue

def test_recherche_et_filtre_dans_le_catalogue(app, alice):
    alice_avec_trois_vins(app, alice)
    assert "Merlot" in page(alice.get("/vins?q=BETA")) and "Zinfandel" not in page(alice.get("/vins?q=BETA"))
    contenu = page(alice.get("/vins?type=blanc"))
    assert "Albarino" in contenu and "Merlot" not in contenu


def test_le_catalogue_se_trie_dans_les_deux_sens(app, alice):
    alice_avec_trois_vins(app, alice)
    croissant = page(alice.get("/vins?tri=millesime&sens=asc"))
    assert apparait_avant(croissant, "Zinfandel", "Merlot") and apparait_avant(croissant, "Merlot", "Albarino")
    decroissant = page(alice.get("/vins?tri=millesime&sens=desc"))
    assert apparait_avant(decroissant, "Albarino", "Merlot") and apparait_avant(decroissant, "Merlot", "Zinfandel")


def test_le_catalogue_montre_aussi_les_vins_dont_on_n_a_aucune_bouteille(app, alice, bob):
    alice_avec_trois_vins(app, alice)
    contenu = page(bob.get("/vins"))                       # Bob n'a rien, mais le catalogue est commun
    assert "Zinfandel" in contenu and "Merlot" in contenu and "Non évalué" in contenu


# Historique

def test_l_historique_se_trie_par_ma_note_dans_les_deux_sens(app, alice):
    alice_avec_trois_vins(app, alice)
    archiver(alice, id_bouteille_du_vin(app, "Zinfandel"), "9")
    archiver(alice, id_bouteille_du_vin(app, "Merlot"), "17")
    archiver(alice, id_bouteille_du_vin(app, "Albarino"), "13")
    croissant = page(alice.get("/historique?tri=ma_note&sens=asc"))
    assert apparait_avant(croissant, "Zinfandel", "Albarino") and apparait_avant(croissant, "Albarino", "Merlot")
    decroissant = page(alice.get("/historique?tri=ma_note&sens=desc"))
    assert apparait_avant(decroissant, "Merlot", "Albarino") and apparait_avant(decroissant, "Albarino", "Zinfandel")


def test_l_historique_est_prive(app, alice, bob):
    alice_avec_trois_vins(app, alice)
    archiver(alice, id_bouteille_du_vin(app, "Merlot"), "17")
    assert "Merlot" in page(alice.get("/historique"))
    assert "Merlot" not in page(bob.get("/historique"))


# Tableau de bord

def test_tableau_de_bord_sans_etagere_affiche_un_etat_explicite(alice):
    contenu = page(alice.get("/"))
    assert "Aucune étagère" in contenu                     # pas de division par zéro
    assert "0.00 €" in contenu


def test_tableau_de_bord_avec_des_bouteilles(app, alice):
    creer_etagere(alice, "E1", "10")
    creer_etagere(alice, "E2", "10")
    vin = creer_vin_complet(alice, "Château Montelena", "Cabernet Sauvignon", "rouge", "1967", "Californie")
    ajouter_bouteilles(alice, vin, id_etagere(app, "alice", "E1"), 5, "20")
    contenu = page(alice.get("/"))
    assert "25.0 %" in contenu and "5 / 20" in contenu     # 5 bouteilles pour une capacité totale de 20
    assert "100.00 €" in contenu                            # 5 bouteilles à 20 euros
    assert "Aucune étagère" not in contenu


def test_tableau_de_bord_apres_un_archivage(app, alice):
    creer_etagere(alice, "E1", "10")
    vin = creer_vin_complet(alice, "Château Montelena", "Cabernet Sauvignon", "rouge", "1967", "Californie")
    ajouter_bouteilles(alice, vin, id_etagere(app, "alice", "E1"), 5, "20")
    archiver(alice, cave_de(app, "alice").bouteilles[0].id, "16")
    contenu = page(alice.get("/"))
    assert "80.00 €" in contenu and "40.0 %" in contenu    # 4 bouteilles restantes sur 10 places
    cave = cave_de(app, "alice")
    assert cave.nb_bouteilles() == 4 and cave.nb_references() == 1 and len(cave.historique()) == 1


def test_le_tableau_de_bord_ne_montre_que_sa_propre_cave(app, alice, bob):
    alice_avec_trois_vins(app, alice)
    contenu_de_bob = page(bob.get("/"))
    assert "Aucune étagère" in contenu_de_bob and "0.00 €" in contenu_de_bob
