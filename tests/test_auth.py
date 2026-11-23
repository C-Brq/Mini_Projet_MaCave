import sqlite3
from contextlib import closing

import pytest

from macave.app import create_app

COMPTE = {
    "identifiant": "alice",
    "email": "alice@example.fr",
    "mot_de_passe": "motdepasse1",
    "confirmation": "motdepasse1",
}


def inscrire(client, **modifs):
    return client.post("/inscription", data={**COMPTE, **modifs})


def connecter(client, identifiant="alice", mot_de_passe="motdepasse1"):
    return client.post("/connexion", data={"identifiant": identifiant, "mot_de_passe": mot_de_passe})


def comptes_en_base(app):
    # Lecture directe de la base
    with closing(sqlite3.connect(app.config["DATABASE"])) as connexion:
        return connexion.execute("SELECT identifiant, email, mot_de_passe_hash FROM utilisateurs").fetchall()


def test_les_pages_s_affichent(client):
    for url in ("/", "/inscription", "/connexion"):
        assert client.get(url).status_code == 200


def test_inscription_enregistre_le_compte_dans_sqlite(app, client):
    reponse = inscrire(client)
    assert reponse.status_code == 302 and reponse.headers["Location"] == "/connexion"
    assert [(i, e) for i, e, _ in comptes_en_base(app)] == [("alice", "alice@example.fr")]


def test_le_mot_de_passe_n_est_jamais_stocke_en_clair(app, client):
    inscrire(client)
    _, _, hache = comptes_en_base(app)[0]
    assert "motdepasse1" not in hache and "$" in hache


def test_email_normalise_en_minuscules(app, client):
    inscrire(client, email="  Alice@Example.FR ")
    assert comptes_en_base(app)[0][1] == "alice@example.fr"


def test_identifiant_deja_utilise_meme_avec_une_autre_casse(app, client):
    inscrire(client)
    reponse = inscrire(client, identifiant="ALICE", email="autre@example.fr")
    assert reponse.status_code == 400
    assert "déjà utilisé" in reponse.get_data(as_text=True)
    assert len(comptes_en_base(app)) == 1


def test_email_deja_utilise(app, client):
    inscrire(client)
    reponse = inscrire(client, identifiant="bob", email="ALICE@example.fr")
    assert reponse.status_code == 400
    assert "adresse e-mail est déjà utilisée" in reponse.get_data(as_text=True)
    assert len(comptes_en_base(app)) == 1


@pytest.mark.parametrize("modifs, message", [
    ({"identifiant": "ab"}, "3 à 30 caractères"),
    ({"identifiant": "avec espace"}, "3 à 30 caractères"),
    ({"email": "pas-un-email"}, "Adresse e-mail invalide"),
    ({"mot_de_passe": "court", "confirmation": "court"}, "au moins 8 caractères"),
    ({"confirmation": "autre-chose"}, "ne correspondent pas"),
])
def test_donnees_invalides_refusees_sans_rien_enregistrer(app, client, modifs, message):
    reponse = inscrire(client, **modifs)
    assert reponse.status_code == 400
    assert message in reponse.get_data(as_text=True)
    assert comptes_en_base(app) == []


def test_formulaire_invalide_garde_les_champs_mais_pas_les_mots_de_passe(client):
    page = inscrire(client, confirmation="autre-chose").get_data(as_text=True)
    assert 'value="alice"' in page and 'value="alice@example.fr"' in page
    assert "motdepasse1" not in page


def test_injection_sql_et_html_sans_effet(app, client):
    inscrire(client, identifiant="x'; DROP TABLE utilisateurs;--")
    page = inscrire(client, email='"><script>alert(1)</script>').get_data(as_text=True)
    assert "<script>alert(1)</script>" not in page          # la saisie est échappée
    assert connecter(client, "' OR '1'='1", "x").status_code == 401
    assert comptes_en_base(app) == []                       # la table existe toujours, et elle est vide


def test_connexion_par_identifiant_ou_par_email_puis_deconnexion(client):
    inscrire(client)
    assert "alice" not in client.get("/").get_data(as_text=True)

    assert connecter(client).status_code == 302
    assert "alice" in client.get("/").get_data(as_text=True)

    assert client.post("/deconnexion").status_code == 302
    assert "Connecté" not in client.get("/").get_data(as_text=True)

    assert connecter(client, "alice@example.fr").status_code == 302   # avec l'e-mail


def test_connexion_refusee_avec_le_meme_message_pour_un_compte_inconnu(client):
    inscrire(client)
    mauvais_mdp = connecter(client, "alice", "faux")
    inconnu = connecter(client, "personne", "motdepasse1")
    assert mauvais_mdp.status_code == inconnu.status_code == 401
    assert "Identifiant ou mot de passe incorrect" in mauvais_mdp.get_data(as_text=True)
    assert "Identifiant ou mot de passe incorrect" in inconnu.get_data(as_text=True)


def test_le_compte_survit_au_redemarrage_de_l_application(app, tmp_path):
    inscrire(app.test_client())
    # « redémarrage » : nouvelle application, même base
    redemarree = create_app({"TESTING": True, "SECRET_KEY": "autre-cle", "CSRF_ACTIVE": False,
                             "DATABASE": app.config["DATABASE"]})
    assert connecter(redemarree.test_client()).status_code == 302
