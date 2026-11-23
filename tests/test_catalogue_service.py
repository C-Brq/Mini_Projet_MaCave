# Catalogue et notes communautaires, sans les pages
import pytest

from macave import db
from macave.auth_service import AuthService
from macave.catalogue_service import CatalogueService
from macave.cave_service import CaveService
from macave.enums import TypeVin
from macave.erreurs import IntrouvableError
from macave.vin import Vin


@pytest.fixture
def connexion(tmp_path):
    connexion = db.connecter(str(tmp_path / "test.db"))
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
def catalogue(connexion):
    return CatalogueService(connexion)


@pytest.fixture
def caves(connexion):
    return CaveService(connexion)


def un_vin():
    return Vin("Château Montelena", "Cabernet Sauvignon", TypeVin.ROUGE, 1967, "Californie")


def deguster(caves, utilisateur, vin, notes):
    # Archive une bouteille par note, renvoie les évaluations
    etagere = caves.creer_etagere(utilisateur, "E1", 20)
    bouteilles = caves.ajouter_bouteilles(utilisateur, vin, etagere.id, len(notes), 20)
    evaluations = []
    for bouteille, note in zip(bouteilles, notes):
        evaluations.append(caves.archiver_bouteille(utilisateur, bouteille.id, note, "Commentaire de " + utilisateur.identifiant))
    return evaluations


# Catalogue

def test_creer_un_vin_puis_le_retrouver(catalogue):
    vin, cree = catalogue.creer_vin(un_vin())
    assert cree is True and vin.id is not None
    assert catalogue.charger_vin(vin.id).nom == "Cabernet Sauvignon"


def test_creer_deux_fois_le_meme_vin_ne_cree_qu_une_reference(catalogue):
    premier, _ = catalogue.creer_vin(un_vin())
    meme_vin = Vin("  CHÂTEAU  montelena ", "cabernet sauvignon", TypeVin.ROUGE, 1967, " californie")
    second, cree = catalogue.creer_vin(meme_vin)
    assert cree is False and second.id == premier.id
    assert len(catalogue.lister_vins()) == 1


def test_un_vin_inexistant_leve_introuvable(catalogue):
    with pytest.raises(IntrouvableError):
        catalogue.charger_vin(9999)


# Notes communautaires

def test_sans_evaluation_la_moyenne_est_absente_et_non_zero(catalogue):
    vin, _ = catalogue.creer_vin(un_vin())
    assert catalogue.note_moyenne(vin.id) == (None, 0)
    assert catalogue.lister_vins()[0]["moyenne"] is None
    assert catalogue.moyennes_par_vin() == {}   # un vin sans note n'apparaît pas dans les moyennes


def test_les_notes_16_12_17_donnent_une_moyenne_de_15(catalogue, caves, alice, bob):
    vin, _ = catalogue.creer_vin(un_vin())
    deguster(caves, alice, vin, [16, 12])
    deguster(caves, bob, vin, [17])
    assert catalogue.note_moyenne(vin.id) == (15, 3)
    assert catalogue.moyennes_par_vin() == {vin.id: (15, 3)}
    assert catalogue.lister_vins()[0]["nb_evaluations"] == 3


def test_modifier_une_note_est_repercute_dans_la_moyenne(catalogue, caves, alice):
    vin, _ = catalogue.creer_vin(un_vin())
    evaluations = deguster(caves, alice, vin, [16, 12, 17])
    caves.modifier_evaluation(alice, evaluations[0].id, 10)   # 16 devient 10 : (10 + 12 + 17) / 3
    assert catalogue.note_moyenne(vin.id) == (13, 3)


def test_plusieurs_degustations_du_meme_utilisateur_comptent_chacune(catalogue, caves, alice):
    vin, _ = catalogue.creer_vin(un_vin())
    deguster(caves, alice, vin, [20, 10])
    assert catalogue.note_moyenne(vin.id) == (15, 2)


def test_les_evaluations_publiees_ne_montrent_que_l_auteur_la_note_le_commentaire_et_la_date(catalogue, caves, alice):
    vin, _ = catalogue.creer_vin(un_vin())
    deguster(caves, alice, vin, [16])
    evaluations = catalogue.evaluations_du_vin(vin.id)
    assert len(evaluations) == 1
    assert evaluations[0]["auteur"] == "alice" and evaluations[0]["note"] == 16
    assert evaluations[0]["commentaire"] == "Commentaire de alice"
    # seulement ces quatre informations, rien sur la cave
    assert sorted(evaluations[0].keys()) == ["auteur", "commentaire", "date", "note"]


def test_les_evaluations_d_un_vin_ne_sont_pas_melangees_avec_celles_d_un_autre(catalogue, caves, alice):
    vin, _ = catalogue.creer_vin(un_vin())
    autre, _ = catalogue.creer_vin(Vin("Domaine X", "Cuvée Y", TypeVin.BLANC, 2020, "Alsace"))
    deguster(caves, alice, vin, [16])
    assert catalogue.evaluations_du_vin(autre.id) == []
    assert catalogue.note_moyenne(autre.id) == (None, 0)
