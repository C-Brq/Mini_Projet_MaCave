# Pages privées : accès, profil, étagères
import pytest

from macave.cave_service import CaveService
from macave.db import get_db
from macave.enums import TypeVin
from macave.utilisateur_repository import UtilisateurRepository
from macave.vin import Vin
from tests.aides import client_connecte, connecter, creer_etagere, id_etagere, page


@pytest.fixture
def alice(app):
    # Client connecté en tant qu'alice
    return client_connecte(app, "alice")


@pytest.fixture
def bob(app):
    return client_connecte(app, "bob")


def remplir_etagere(app, identifiant, nom_etagere, quantite):
    # Range des bouteilles via le service
    with app.app_context():
        connexion = get_db()
        utilisateur = UtilisateurRepository(connexion).trouver_par_identifiant_ou_email(identifiant)
        vin = Vin("Château Montelena", "Cabernet Sauvignon", TypeVin.ROUGE, 1967, "Californie")
        CaveService(connexion).ajouter_bouteilles(
            utilisateur, vin, id_etagere(app, identifiant, nom_etagere), quantite, 20)


# Contrôle d'accès

@pytest.mark.parametrize("url", ["/etageres", "/etageres/1", "/profil"])
def test_pages_protegees_renvoient_vers_la_connexion_quand_on_n_est_pas_connecte(client, url):
    reponse = client.get(url)
    assert reponse.status_code == 302 and reponse.headers["Location"] == "/connexion"


@pytest.mark.parametrize("url", ["/etageres", "/etageres/1/modifier", "/etageres/1/supprimer", "/profil"])
def test_envois_de_formulaires_refuses_quand_on_n_est_pas_connecte(client, url):
    reponse = client.post(url, data={"nom": "E1", "capacite": "10"})
    assert reponse.status_code == 302 and reponse.headers["Location"] == "/connexion"


def test_le_message_de_connexion_requise_s_affiche(client):
    suite = client.get("/etageres", follow_redirects=True)
    assert "Connectez-vous pour accéder à cette page." in page(suite)


def test_une_adresse_inconnue_donne_la_page_introuvable(client):
    reponse = client.get("/cette-page-n-existe-pas")
    assert reponse.status_code == 404 and "Page introuvable" in page(reponse)


# Étagères

def test_creer_une_etagere_de_capacite_10_affiche_0_sur_10(alice):
    contenu = page(creer_etagere(alice, "E1", "10"))
    # pas d'apostrophe : Jinja l'échappe en &#39;
    assert "a été créée." in contenu
    assert "E1" in contenu and "0 / 10" in contenu


@pytest.mark.parametrize("nom, capacite, message", [
    ("", "10", "ne peut pas être vide"),
    ("E1", "abc", "doit être un nombre entier"),
    ("E1", "2.5", "doit être un nombre entier"),
    ("E1", "", "doit être un nombre entier"),
    ("E1", "0", "strictement positif"),
    ("E1", "-3", "strictement positif"),
    ("E1", "1" + "0" * 20, "strictement positif"),   # trop grand pour SQLite : refusé sans erreur 500
    ("x" * 101, "10", "ne peut pas dépasser 100 caractères"),
])
def test_etagere_invalide_refusee_avec_un_message(alice, app, nom, capacite, message):
    contenu = page(creer_etagere(alice, nom, capacite))
    assert message in contenu
    assert id_etagere(app, "alice", nom) is None  # rien n'a été créé


def test_nom_d_etagere_deja_utilise_refuse(alice):
    creer_etagere(alice, "E1", "10")
    contenu = page(creer_etagere(alice, " e1 ", "5"))
    assert "porte déjà ce nom" in contenu


def test_la_fiche_d_une_etagere_s_affiche(alice, app):
    creer_etagere(alice, "E1", "10")
    reponse = alice.get("/etageres/" + str(id_etagere(app, "alice", "E1")))
    assert reponse.status_code == 200
    assert "E1" in page(reponse) and "Cette étagère est vide." in page(reponse)


def test_supprimer_une_etagere_demande_une_confirmation(alice, app):
    creer_etagere(alice, "E1", "10")
    contenu = page(alice.get("/etageres/" + str(id_etagere(app, "alice", "E1"))))
    assert "confirm(" in contenu


def test_la_fiche_montre_les_bouteilles_et_l_occupation(alice, app):
    creer_etagere(alice, "E1", "10")
    remplir_etagere(app, "alice", "E1", 5)
    contenu = page(alice.get("/etageres/" + str(id_etagere(app, "alice", "E1"))))
    assert "5 / 10" in contenu and "Cabernet Sauvignon" in contenu


def test_modifier_une_etagere(alice, app):
    creer_etagere(alice, "E1", "10")
    identifiant = id_etagere(app, "alice", "E1")
    suite = alice.post(f"/etageres/{identifiant}/modifier",
                       data={"nom": "Cave du fond", "capacite": "20"}, follow_redirects=True)
    assert "a été modifiée." in page(suite)
    assert "Cave du fond" in page(suite) and "0 / 20" in page(suite)


def test_reduire_la_capacite_sous_l_occupation_est_refuse(alice, app):
    creer_etagere(alice, "E1", "10")
    remplir_etagere(app, "alice", "E1", 5)
    identifiant = id_etagere(app, "alice", "E1")
    suite = alice.post(f"/etageres/{identifiant}/modifier",
                       data={"nom": "E1", "capacite": "4"}, follow_redirects=True)
    assert "ne peut pas être inférieure à l" in page(suite)
    assert "5 / 10" in page(suite)


def test_supprimer_une_etagere_vide(alice, app):
    creer_etagere(alice, "E1", "10")
    identifiant = id_etagere(app, "alice", "E1")
    suite = alice.post(f"/etageres/{identifiant}/supprimer", follow_redirects=True)
    assert "a été supprimée." in page(suite)
    assert id_etagere(app, "alice", "E1") is None


def test_supprimer_une_etagere_non_vide_est_refuse_avec_un_message(alice, app):
    creer_etagere(alice, "E1", "10")
    remplir_etagere(app, "alice", "E1", 1)
    identifiant = id_etagere(app, "alice", "E1")
    suite = alice.post(f"/etageres/{identifiant}/supprimer", follow_redirects=True)
    assert "pas vide" in page(suite)
    assert id_etagere(app, "alice", "E1") == identifiant


# R1 : cave d'un autre inaccessible, même par URL

def test_la_liste_des_etageres_ne_montre_que_les_siennes(alice, bob):
    creer_etagere(alice, "Etagere-d-alice", "10")
    creer_etagere(bob, "Etagere-de-bob", "10")
    assert "Etagere-d-alice" in page(alice.get("/etageres"))
    assert "Etagere-de-bob" not in page(alice.get("/etageres"))
    assert "Etagere-d-alice" not in page(bob.get("/etageres"))


def test_acces_direct_a_l_etagere_d_un_autre_utilisateur_refuse(alice, bob, app):
    creer_etagere(alice, "E1", "10")
    identifiant = id_etagere(app, "alice", "E1")
    assert bob.get(f"/etageres/{identifiant}").status_code == 404
    assert bob.post(f"/etageres/{identifiant}/modifier", data={"nom": "Volée", "capacite": "99"}).status_code == 404
    assert bob.post(f"/etageres/{identifiant}/supprimer").status_code == 404
    # l'étagère d'Alice n'a pas bougé
    assert id_etagere(app, "alice", "E1") == identifiant
    assert "0 / 10" in page(alice.get(f"/etageres/{identifiant}"))


def test_une_etagere_qui_n_existe_pas_donne_404(alice):
    assert alice.get("/etageres/9999").status_code == 404


# Profil

def test_le_profil_s_affiche_avec_l_email_actuel(alice):
    reponse = alice.get("/profil")
    assert reponse.status_code == 200 and "alice@example.fr" in page(reponse)


def test_modifier_son_email(alice):
    suite = alice.post("/profil", data={"email": "  Nouvelle@Example.FR "}, follow_redirects=True)
    assert "Votre profil a été mis à jour." in page(suite)
    assert "nouvelle@example.fr" in page(alice.get("/profil"))


def test_email_invalide_refuse(alice):
    reponse = alice.post("/profil", data={"email": "pas-un-email"})
    assert reponse.status_code == 400 and "Adresse e-mail invalide" in page(reponse)


def test_email_deja_utilise_par_un_autre_compte_refuse(alice, bob):
    reponse = alice.post("/profil", data={"email": "bob@example.fr"})
    assert reponse.status_code == 400 and "déjà utilisée" in page(reponse)
    assert "alice@example.fr" in page(alice.get("/profil"))


def test_changer_de_mot_de_passe(alice, app):
    suite = alice.post("/profil", data={
        "email": "alice@example.fr", "mot_de_passe_actuel": "motdepasse1",
        "nouveau_mot_de_passe": "nouveaumdp99", "confirmation": "nouveaumdp99"}, follow_redirects=True)
    assert "Votre profil a été mis à jour." in page(suite)
    assert connecter(app.test_client(), "alice", "motdepasse1").status_code == 401   # l'ancien ne marche plus
    assert connecter(app.test_client(), "alice", "nouveaumdp99").status_code == 302  # le nouveau oui


@pytest.mark.parametrize("donnees, message", [
    ({"mot_de_passe_actuel": "faux", "nouveau_mot_de_passe": "nouveaumdp99", "confirmation": "nouveaumdp99"},
     "mot de passe actuel est incorrect"),
    ({"mot_de_passe_actuel": "motdepasse1", "nouveau_mot_de_passe": "court", "confirmation": "court"},
     "au moins 8 caractères"),
    ({"mot_de_passe_actuel": "motdepasse1", "nouveau_mot_de_passe": "nouveaumdp99", "confirmation": "autre"},
     "ne correspondent pas"),
])
def test_changement_de_mot_de_passe_invalide_refuse(alice, app, donnees, message):
    donnees["email"] = "alice@example.fr"
    reponse = alice.post("/profil", data=donnees)
    assert reponse.status_code == 400 and message in page(reponse)
    assert connecter(app.test_client(), "alice", "motdepasse1").status_code == 302  # l'ancien marche toujours


# Navigation

def test_l_en_tete_propose_les_etageres_et_le_profil_une_fois_connecte(alice):
    contenu = page(alice.get("/"))
    assert "/etageres" in contenu and "/profil" in contenu and "Déconnexion" in contenu
