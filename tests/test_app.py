# Clé secrète et création de la base
import sqlite3
from contextlib import closing

from flask import Flask

from macave.app import _cle_secrete, create_app


def test_la_cle_secrete_peut_venir_de_l_environnement(tmp_path, monkeypatch):
    monkeypatch.setenv("MACAVE_SECRET_KEY", "cle-venue-de-l-environnement")
    app = create_app({"DATABASE": str(tmp_path / "t.db")})
    assert app.config["SECRET_KEY"] == "cle-venue-de-l-environnement"


def test_sans_cle_configuree_la_connexion_fonctionne_quand_meme(tmp_path, monkeypatch):
    # lancement normal : SECRET_KEY à None
    monkeypatch.setenv("MACAVE_SECRET_KEY", "cle-de-test")
    client = create_app({"TESTING": True, "CSRF_ACTIVE": False, "DATABASE": str(tmp_path / "t.db")}).test_client()
    client.post("/inscription", data={"identifiant": "alice", "email": "a@example.fr",
                                      "mot_de_passe": "motdepasse1", "confirmation": "motdepasse1"})
    reponse = client.post("/connexion", data={"identifiant": "alice", "mot_de_passe": "motdepasse1"})
    assert reponse.status_code == 302


def test_la_cle_secrete_est_generee_une_fois_puis_reutilisee(tmp_path, monkeypatch):
    monkeypatch.delenv("MACAVE_SECRET_KEY", raising=False)
    app = Flask("test", instance_path=str(tmp_path / "instance"))
    premiere = _cle_secrete(app)
    assert len(premiere) == 64
    assert (tmp_path / "instance" / "secret_key").exists()
    assert _cle_secrete(app) == premiere


def test_la_base_et_sa_table_sont_creees_au_demarrage(tmp_path):
    chemin = tmp_path / "dossier" / "macave.db"   # le dossier n'existe pas encore
    create_app({"TESTING": True, "SECRET_KEY": "x", "DATABASE": str(chemin)})
    with closing(sqlite3.connect(chemin)) as connexion:
        tables = [t for (t,) in connexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    assert "utilisateurs" in tables


def test_demarrer_deux_fois_ne_perd_pas_les_donnees(tmp_path):
    chemin = str(tmp_path / "macave.db")
    config = {"TESTING": True, "SECRET_KEY": "x", "CSRF_ACTIVE": False, "DATABASE": chemin}
    create_app(config).test_client().post("/inscription", data={
        "identifiant": "alice", "email": "a@example.fr", "mot_de_passe": "motdepasse1", "confirmation": "motdepasse1"})
    create_app(config)  # schéma rejoué sans effacer les comptes
    with closing(sqlite3.connect(chemin)) as connexion:
        assert connexion.execute("SELECT COUNT(*) FROM utilisateurs").fetchone() == (1,)
