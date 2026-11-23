# CSRF actif ici : le jeton est lu dans les pages, comme un navigateur
import re
from pathlib import Path

import pytest

from macave.app import create_app
from macave.db import get_db
from macave.utilisateur_repository import UtilisateurRepository
from tests.aides import page

DOSSIER_TEMPLATES = Path(__file__).parent.parent / "macave" / "templates"

COMPTE = {"identifiant": "alice", "email": "alice@example.fr",
          "mot_de_passe": "motdepasse1", "confirmation": "motdepasse1"}


@pytest.fixture
def app_csrf(tmp_path):
    return create_app({"TESTING": True, "SECRET_KEY": "cle-de-test", "CSRF_ACTIVE": True,
                       "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def client(app_csrf):
    return app_csrf.test_client()


def jeton_de(client, url):
    # Renvoie le jeton caché de la page
    contenu = page(client.get(url))
    return re.search(r'name="csrf" value="([0-9a-f]+)"', contenu).group(1)


def compte_existe(app, identifiant):
    with app.app_context():
        return UtilisateurRepository(get_db()).trouver_par_identifiant_ou_email(identifiant) is not None


def inscrire_et_connecter(client):
    # Envoie chaque formulaire avec le jeton de sa page
    client.post("/inscription", data=dict(COMPTE, csrf=jeton_de(client, "/inscription")))
    return client.post("/connexion", data={"identifiant": "alice", "mot_de_passe": "motdepasse1",
                                           "csrf": jeton_de(client, "/connexion")})


# Le jeton est dans les pages

def test_chaque_formulaire_post_de_chaque_page_contient_le_jeton():
    # lecture directe des templates
    for fichier in DOSSIER_TEMPLATES.glob("*.html"):
        texte = fichier.read_text(encoding="utf-8")
        assert texte.count('method="post"') == texte.count('name="csrf"'), fichier.name


def test_le_jeton_ne_change_pas_pendant_la_session(client):
    assert jeton_de(client, "/connexion") == jeton_de(client, "/inscription")


def test_deux_visiteurs_n_ont_pas_le_meme_jeton(app_csrf):
    assert jeton_de(app_csrf.test_client(), "/connexion") != jeton_de(app_csrf.test_client(), "/connexion")


# Envois refusés sans le bon jeton

def test_inscription_sans_jeton_refusee(app_csrf, client):
    client.get("/inscription")
    reponse = client.post("/inscription", data=COMPTE)
    assert reponse.status_code == 400 and "Formulaire refusé" in page(reponse)
    assert not compte_existe(app_csrf, "alice")


def test_inscription_sans_avoir_ouvert_la_page_refusee(app_csrf, client):
    # aucun jeton donné : refusé même avec un champ csrf
    assert client.post("/inscription", data=dict(COMPTE, csrf="n-importe-quoi")).status_code == 400
    assert not compte_existe(app_csrf, "alice")


def test_inscription_avec_un_mauvais_jeton_refusee(app_csrf, client):
    client.get("/inscription")
    assert client.post("/inscription", data=dict(COMPTE, csrf="faux")).status_code == 400
    assert not compte_existe(app_csrf, "alice")


def test_jeton_avec_des_caracteres_non_ascii_refuse_sans_planter(client):
    client.get("/inscription")
    assert client.post("/inscription", data=dict(COMPTE, csrf="é à ü ✓")).status_code == 400


def test_le_jeton_d_un_autre_navigateur_est_refuse(app_csrf, client):
    jeton_d_un_autre = jeton_de(app_csrf.test_client(), "/inscription")
    client.get("/inscription")
    assert client.post("/inscription", data=dict(COMPTE, csrf=jeton_d_un_autre)).status_code == 400
    assert not compte_existe(app_csrf, "alice")


def test_connexion_sans_jeton_refusee(app_csrf, client):
    inscrire_et_connecter(client)
    client.post("/deconnexion", data={"csrf": jeton_de(client, "/")})
    reponse = client.post("/connexion", data={"identifiant": "alice", "mot_de_passe": "motdepasse1"})
    assert reponse.status_code == 400
    assert client.get("/etageres").status_code == 302   # toujours pas connecté


# Avec le bon jeton

def test_le_parcours_normal_fonctionne_avec_les_jetons(app_csrf, client):
    assert inscrire_et_connecter(client).status_code == 302
    assert compte_existe(app_csrf, "alice")

    reponse = client.post("/etageres", follow_redirects=True,
                          data={"nom": "E1", "capacite": "10", "csrf": jeton_de(client, "/etageres")})
    assert "a été créée." in page(reponse) and "0 / 10" in page(reponse)


def test_une_action_sensible_sans_jeton_est_refusee_et_ne_fait_rien(client):
    inscrire_et_connecter(client)
    client.post("/etageres", data={"nom": "E1", "capacite": "10", "csrf": jeton_de(client, "/etageres")})

    # envoi pirate : cookie présent, mais pas le jeton
    reponse = client.post("/etageres", data={"nom": "E2", "capacite": "5"})
    assert reponse.status_code == 400
    contenu = page(client.get("/etageres"))
    assert "E1" in contenu and "E2" not in contenu


def test_la_suppression_d_une_etagere_sans_jeton_est_refusee(client):
    inscrire_et_connecter(client)
    client.post("/etageres", data={"nom": "E1", "capacite": "10", "csrf": jeton_de(client, "/etageres")})
    url = re.search(r"/etageres/(\d+)", page(client.get("/etageres"))).group(0)

    assert client.post(url + "/supprimer").status_code == 400
    assert "E1" in page(client.get("/etageres"))   # l'étagère existe toujours


def test_la_deconnexion_exige_le_jeton(client):
    inscrire_et_connecter(client)
    assert client.post("/deconnexion").status_code == 400
    assert client.get("/etageres").status_code == 200   # toujours connecté

    assert client.post("/deconnexion", data={"csrf": jeton_de(client, "/etageres")}).status_code == 302
    assert client.get("/etageres").status_code == 302   # déconnecté


def test_les_consultations_n_ont_pas_besoin_de_jeton(client):
    assert client.get("/").status_code == 200
    assert client.get("/connexion").status_code == 200
