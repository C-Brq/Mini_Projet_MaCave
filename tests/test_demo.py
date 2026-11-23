# Jeu de démonstration
import pytest

from macave import db
from macave.demo import creer_donnees_demo
from tests.aides import connecter, page


@pytest.fixture
def connexion(app):
    # Connexion à la base vide de test
    connexion = db.connecter(app.config["DATABASE"])
    yield connexion
    connexion.close()


def compter(connexion, table):
    return connexion.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]


def test_la_demo_cree_deux_utilisateurs_plusieurs_etageres_et_plusieurs_vins(connexion):
    creer_donnees_demo(connexion)
    assert compter(connexion, "utilisateurs") == 2
    assert compter(connexion, "caves") == 2
    assert compter(connexion, "etageres") >= 3
    assert compter(connexion, "vins") >= 5


def test_la_demo_contient_des_exemplaires_identiques_d_une_seule_reference(connexion):
    creer_donnees_demo(connexion)
    # plusieurs exemplaires, une seule ligne dans vins
    ligne = connexion.execute(
        "SELECT vin_id, COUNT(*) AS n FROM bouteilles GROUP BY vin_id ORDER BY n DESC").fetchone()
    assert ligne["n"] >= 5
    assert compter(connexion, "vins") < compter(connexion, "bouteilles")


def test_la_demo_contient_des_evaluations_et_la_moyenne_du_montelena_est_15(connexion):
    creer_donnees_demo(connexion)
    assert compter(connexion, "evaluations") >= 4
    moyenne = connexion.execute(
        "SELECT AVG(e.note) FROM evaluations e JOIN vins v ON v.id = e.vin_id"
        " WHERE v.nom = 'Cabernet Sauvignon'").fetchone()[0]
    assert moyenne == 15   # (16 + 12 + 17) / 3


def test_la_demo_est_coherente_avec_les_regles(connexion):
    creer_donnees_demo(connexion)
    # aucune étagère ne dépasse sa capacité
    depassements = connexion.execute(
        "SELECT e.nom FROM etageres e WHERE e.capacite_max <"
        " (SELECT COUNT(*) FROM bouteilles b WHERE b.etagere_id = e.id)").fetchall()
    assert depassements == []
    # bouteilles archivées hors étagère
    assert connexion.execute(
        "SELECT COUNT(*) FROM bouteilles WHERE statut = 'archivee' AND etagere_id IS NOT NULL").fetchone()[0] == 0


def test_la_demo_refuse_de_s_executer_sur_une_base_non_vide(connexion):
    creer_donnees_demo(connexion)
    with pytest.raises(ValueError):
        creer_donnees_demo(connexion)
    assert compter(connexion, "utilisateurs") == 2   # rien n'a été ajouté ni effacé


def test_on_peut_se_connecter_avec_les_comptes_de_demo_et_voir_son_tableau_de_bord(app, connexion):
    creer_donnees_demo(connexion)
    client = app.test_client()
    assert connecter(client, "alice", "motdepasse1").status_code == 302
    contenu = page(client.get("/"))
    assert "Tableau de bord" in contenu and "Aucune étagère" not in contenu
    assert "Cave principale" in page(client.get("/etageres"))
    # le second compte ne voit pas les étagères du premier
    autre = app.test_client()
    assert connecter(autre, "bob", "motdepasse2").status_code == 302
    assert "Cave principale" not in page(autre.get("/etageres"))
    assert "Cave à vin" in page(autre.get("/etageres"))


def test_le_montelena_partage_montre_les_evaluations_aux_deux_comptes(app, connexion):
    creer_donnees_demo(connexion)
    for identifiant, mot_de_passe in (("alice", "motdepasse1"), ("bob", "motdepasse2")):
        client = app.test_client()
        connecter(client, identifiant, mot_de_passe)
        vin_id = connexion.execute("SELECT id FROM vins WHERE nom = 'Cabernet Sauvignon'").fetchone()[0]
        contenu = page(client.get(f"/vins/{vin_id}"))
        assert "15 / 20" in contenu and "3 évaluations" in contenu
