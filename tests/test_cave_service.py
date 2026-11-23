# CaveService et persistance, sur une vraie base SQLite sans Flask
import sqlite3
from datetime import date

import pytest

from macave import db
from macave.auth_service import AuthService
from macave.cave_service import CaveService
from macave.enums import TypeVin
from macave.erreurs import IntrouvableError
from macave.vin import Vin


@pytest.fixture
def chemin_base(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def connexion(chemin_base):
    connexion = db.connecter(chemin_base)
    db.initialiser_schema(connexion)
    yield connexion
    connexion.close()


@pytest.fixture
def alice(connexion):
    return AuthService(connexion).inscrire("alice", "alice@example.fr", "motdepasse1", "motdepasse1")


@pytest.fixture
def bob(connexion):
    return AuthService(connexion).inscrire("bob", "bob@example.fr", "motdepasse2", "motdepasse2")


@pytest.fixture
def service(connexion):
    return CaveService(connexion)


def un_vin():
    return Vin("Château Montelena", "Cabernet Sauvignon", TypeVin.ROUGE, 1967, "Californie")


def compter(connexion, table):
    # Nombre de lignes d'une table
    return connexion.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]


# Compte et cave

def test_l_inscription_cree_la_cave_privee(connexion, alice, service):
    assert compter(connexion, "caves") == 1
    cave = service.charger_cave(alice)
    assert cave.etageres == [] and cave.bouteilles == []


def test_un_ancien_compte_sans_cave_en_recoit_une(connexion, alice, service):
    connexion.execute("DELETE FROM caves")  # compte créé avant l'ajout des caves
    connexion.commit()
    assert service.charger_cave(alice).etageres == []
    assert compter(connexion, "caves") == 1


# Étagères

def test_etagere_de_capacite_10_est_a_0_sur_10(alice, service):
    service.creer_etagere(alice, "E1", 10)
    etagere = service.charger_cave(alice).etageres[0]
    assert (etagere.nom, etagere.occupation, etagere.capacite_max) == ("E1", 0, 10)


def test_nom_d_etagere_deja_pris_refuse(alice, service, connexion):
    service.creer_etagere(alice, "E1", 10)
    with pytest.raises(ValueError):
        service.creer_etagere(alice, " e1 ", 5)
    assert compter(connexion, "etageres") == 1


def test_deux_utilisateurs_peuvent_avoir_une_etagere_du_meme_nom(alice, bob, service):
    service.creer_etagere(alice, "E1", 10)
    service.creer_etagere(bob, "E1", 10)


def test_modifier_une_etagere(alice, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    service.modifier_etagere(alice, etagere.id, "Cave du fond", 20)
    rechargee = service.charger_cave(alice).etageres[0]
    assert (rechargee.nom, rechargee.capacite_max) == ("Cave du fond", 20)


def test_capacite_sous_l_occupation_refusee_sans_rien_changer(alice, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    service.ajouter_bouteilles(alice, un_vin(), etagere.id, 5, 20)
    with pytest.raises(ValueError):
        service.modifier_etagere(alice, etagere.id, "Nouveau nom", 4)
    rechargee = service.charger_cave(alice).etageres[0]
    assert (rechargee.nom, rechargee.capacite_max) == ("E1", 10)


def test_supprimer_une_etagere_non_vide_refuse(alice, service, connexion):
    etagere = service.creer_etagere(alice, "E1", 10)
    service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)
    with pytest.raises(ValueError):
        service.supprimer_etagere(alice, etagere.id)
    assert compter(connexion, "etageres") == 1


def test_supprimer_une_etagere_vide(alice, service, connexion):
    etagere = service.creer_etagere(alice, "E1", 10)
    service.supprimer_etagere(alice, etagere.id)
    assert compter(connexion, "etageres") == 0


# Ajout, déplacement, retrait, archivage

def test_cinq_bouteilles_identiques_sont_cinq_exemplaires_et_une_seule_reference(alice, service, connexion):
    etagere = service.creer_etagere(alice, "E1", 10)
    service.ajouter_bouteilles(alice, un_vin(), etagere.id, 5, 20)
    cave = service.charger_cave(alice)
    assert cave.nb_bouteilles() == 5 and cave.nb_references() == 1
    assert compter(connexion, "bouteilles") == 5 and compter(connexion, "vins") == 1


def test_ajouter_le_meme_vin_ecrit_autrement_ne_cree_pas_de_doublon(alice, service, connexion):
    etagere = service.creer_etagere(alice, "E1", 10)
    service.ajouter_bouteilles(alice, un_vin(), etagere.id, 2, 20)
    meme_vin = Vin("  château MONTELENA ", "cabernet  sauvignon", TypeVin.ROUGE, 1967, "californie")
    service.ajouter_bouteilles(alice, meme_vin, etagere.id, 3, 25)
    assert compter(connexion, "vins") == 1
    assert service.charger_cave(alice).nb_references() == 1


def test_ajout_de_6_bouteilles_sur_une_etagere_a_5_sur_10_est_refuse_sans_ajout_partiel(alice, service, connexion):
    etagere = service.creer_etagere(alice, "E1", 10)
    service.ajouter_bouteilles(alice, un_vin(), etagere.id, 5, 20)
    autre_vin = Vin("Domaine X", "Cuvée Y", TypeVin.BLANC, 2020, "Alsace")
    with pytest.raises(ValueError):
        service.ajouter_bouteilles(alice, autre_vin, etagere.id, 6, 20)
    assert compter(connexion, "bouteilles") == 5
    assert compter(connexion, "vins") == 1  # la nouvelle référence est annulée aussi
    assert service.charger_cave(alice).etageres[0].occupation == 5


def test_deplacer_une_bouteille_met_a_jour_les_deux_etageres(alice, service):
    e1 = service.creer_etagere(alice, "E1", 10)
    e2 = service.creer_etagere(alice, "E2", 10)
    bouteilles = service.ajouter_bouteilles(alice, un_vin(), e1.id, 5, 20)
    service.deplacer_bouteille(alice, bouteilles[0].id, e2.id)
    etageres = service.charger_cave(alice).etageres
    assert [(e.nom, e.occupation) for e in etageres] == [("E1", 4), ("E2", 1)]


def test_deplacer_vers_une_etagere_pleine_est_refuse_sans_rien_changer(alice, service):
    e1 = service.creer_etagere(alice, "E1", 10)
    e2 = service.creer_etagere(alice, "E2", 1)
    bouteilles = service.ajouter_bouteilles(alice, un_vin(), e1.id, 2, 20)
    service.deplacer_bouteille(alice, bouteilles[0].id, e2.id)
    with pytest.raises(ValueError):
        service.deplacer_bouteille(alice, bouteilles[1].id, e2.id)
    etageres = service.charger_cave(alice).etageres
    assert [(e.nom, e.occupation) for e in etageres] == [("E1", 1), ("E2", 1)]


def test_archiver_un_exemplaire_parmi_cinq(alice, service, connexion):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteilles = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 5, 20)
    service.archiver_bouteille(alice, bouteilles[0].id, 16, "Très bon")
    cave = service.charger_cave(alice)
    assert cave.nb_bouteilles() == 4 and len(cave.historique()) == 1
    assert cave.etageres[0].occupation == 4  # l'exemplaire archivé n'occupe plus de place
    archivee = cave.historique()[0]
    assert archivee.evaluation.note == 16 and archivee.evaluation.commentaire == "Très bon"
    assert archivee.date_sortie == date.today()
    assert compter(connexion, "evaluations") == 1


def test_archiver_avant_la_date_d_ajout_est_refuse_et_rien_n_est_enregistre(alice, service, connexion):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteille = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)[0]   # ajoutée aujourd'hui
    with pytest.raises(ValueError):
        service.archiver_bouteille(alice, bouteille.id, 15, "Bon", date(2000, 1, 1))
    assert service.charger_cave(alice).nb_bouteilles() == 1
    assert compter(connexion, "evaluations") == 0


def test_ajouter_des_bouteilles_a_une_date_choisie_puis_les_archiver_plus_tard(alice, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteille = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20, date(2024, 1, 10))[0]
    service.archiver_bouteille(alice, bouteille.id, 15, None, date(2024, 6, 1))
    archivee = service.charger_cave(alice).historique()[0]
    assert archivee.date_ajout == date(2024, 1, 10) and archivee.date_sortie == date(2024, 6, 1)


def test_une_bouteille_archivee_ne_peut_etre_ni_archivee_ni_retiree(alice, service, connexion):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteille = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)[0]
    service.archiver_bouteille(alice, bouteille.id, 14)
    with pytest.raises(ValueError):
        service.archiver_bouteille(alice, bouteille.id, 18)
    with pytest.raises(ValueError):
        service.retirer_bouteille(alice, bouteille.id)
    assert compter(connexion, "evaluations") == 1


def test_note_hors_bornes_refusee_et_la_bouteille_reste_en_stock(alice, service, connexion):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteille = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)[0]
    with pytest.raises(ValueError):
        service.archiver_bouteille(alice, bouteille.id, 21)
    assert service.charger_cave(alice).nb_bouteilles() == 1
    assert compter(connexion, "evaluations") == 0


def test_retrait_definitif_garde_la_reference_dans_le_catalogue(alice, service, connexion):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteilles = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 5, 20)
    service.retirer_bouteille(alice, bouteilles[0].id)
    cave = service.charger_cave(alice)
    assert cave.nb_bouteilles() == 4 and cave.historique() == []
    assert compter(connexion, "vins") == 1


def test_modifier_prix_et_date_d_une_bouteille(alice, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteille = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)[0]
    service.modifier_bouteille(alice, bouteille.id, 35.5, date(2024, 5, 17))
    rechargee = service.charger_cave(alice).bouteilles[0]
    assert rechargee.prix_achat == 35.5 and rechargee.date_ajout == date(2024, 5, 17)


def test_modifier_une_evaluation(alice, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteille = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)[0]
    evaluation = service.archiver_bouteille(alice, bouteille.id, 10, "Bof")
    service.modifier_evaluation(alice, evaluation.id, 18, "Finalement très bon")
    rechargee = service.charger_cave(alice).historique()[0].evaluation
    assert (rechargee.note, rechargee.commentaire) == (18, "Finalement très bon")


# R1 : jamais la cave d'un autre

def test_un_autre_utilisateur_ne_voit_rien_de_la_cave(alice, bob, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    service.ajouter_bouteilles(alice, un_vin(), etagere.id, 3, 20)
    cave_de_bob = service.charger_cave(bob)
    assert cave_de_bob.etageres == [] and cave_de_bob.bouteilles == []


def test_un_autre_utilisateur_ne_peut_rien_modifier(alice, bob, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteille = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)[0]
    service.creer_etagere(bob, "B1", 10)
    etagere_de_bob = service.charger_cave(bob).etageres[0]

    with pytest.raises(IntrouvableError):
        service.modifier_etagere(bob, etagere.id, "Volée", 10)
    with pytest.raises(IntrouvableError):
        service.supprimer_etagere(bob, etagere.id)
    with pytest.raises(IntrouvableError):
        service.deplacer_bouteille(bob, bouteille.id, etagere_de_bob.id)
    with pytest.raises(IntrouvableError):
        service.retirer_bouteille(bob, bouteille.id)
    with pytest.raises(IntrouvableError):
        service.archiver_bouteille(bob, bouteille.id, 10)
    with pytest.raises(IntrouvableError):
        service.ajouter_bouteilles(bob, un_vin(), etagere.id, 1, 20)  # sur l'étagère d'Alice
    # et la cave d'Alice n'a pas bougé
    cave = service.charger_cave(alice)
    assert cave.nb_bouteilles() == 1 and cave.etageres[0].nom == "E1"


def test_un_autre_utilisateur_ne_peut_pas_modifier_une_evaluation(alice, bob, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteille = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)[0]
    evaluation = service.archiver_bouteille(alice, bouteille.id, 10)
    with pytest.raises(IntrouvableError):
        service.modifier_evaluation(bob, evaluation.id, 20)
    assert service.charger_cave(alice).historique()[0].evaluation.note == 10


# Persistance

def test_la_cave_survit_au_redemarrage(chemin_base, alice, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteilles = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 5, 20)
    service.archiver_bouteille(alice, bouteilles[0].id, 16, "Excellent")

    # « redémarrage » : nouvelle connexion, même fichier
    nouvelle = db.connecter(chemin_base)
    try:
        cave = CaveService(nouvelle).charger_cave(alice)
        assert [(e.nom, e.occupation) for e in cave.etageres] == [("E1", 4)]
        assert cave.nb_bouteilles() == 4 and len(cave.historique()) == 1
        assert cave.historique()[0].evaluation.commentaire == "Excellent"
    finally:
        nouvelle.close()


# Contraintes de la base

def test_la_base_refuse_une_note_hors_bornes(connexion, alice, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteille = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)[0]
    service.archiver_bouteille(alice, bouteille.id, 10)
    with pytest.raises(sqlite3.IntegrityError):
        connexion.execute("UPDATE evaluations SET note = 21")


def test_la_base_refuse_une_bouteille_en_stock_sans_etagere(connexion, alice, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    bouteille = service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)[0]
    with pytest.raises(sqlite3.IntegrityError):
        connexion.execute("UPDATE bouteilles SET etagere_id = NULL WHERE id = ?", (bouteille.id,))


def test_la_base_refuse_de_supprimer_une_etagere_qui_contient_des_bouteilles(connexion, alice, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)
    with pytest.raises(sqlite3.IntegrityError):
        connexion.execute("DELETE FROM etageres WHERE id = ?", (etagere.id,))


def test_la_base_refuse_deux_fois_la_meme_reference(connexion, alice, service):
    etagere = service.creer_etagere(alice, "E1", 10)
    service.ajouter_bouteilles(alice, un_vin(), etagere.id, 1, 20)
    with pytest.raises(sqlite3.IntegrityError):
        connexion.execute(
            "INSERT INTO vins (domaine, nom, type, millesime, region, cle_identite)"
            " VALUES ('x', 'x', 'rouge', 2000, 'x', ?)", (un_vin().cle_identite(),))
