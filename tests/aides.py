# Fonctions communes aux tests des pages
from macave.cave_service import CaveService
from macave.db import get_db
from macave.utilisateur_repository import UtilisateurRepository


def creer_compte(client, identifiant):
    client.post("/inscription", data={
        "identifiant": identifiant, "email": identifiant + "@example.fr",
        "mot_de_passe": "motdepasse1", "confirmation": "motdepasse1"})


def connecter(client, identifiant, mot_de_passe="motdepasse1"):
    return client.post("/connexion", data={"identifiant": identifiant, "mot_de_passe": mot_de_passe})


def client_connecte(app, identifiant):
    # Client de test inscrit et connecté
    client = app.test_client()
    creer_compte(client, identifiant)
    connecter(client, identifiant)
    return client


def page(reponse):
    # Texte HTML de la réponse
    return reponse.get_data(as_text=True)


def cave_de(app, identifiant):
    # Cave lue directement dans la base
    with app.app_context():
        connexion = get_db()
        utilisateur = UtilisateurRepository(connexion).trouver_par_identifiant_ou_email(identifiant)
        return CaveService(connexion).charger_cave(utilisateur)


def id_etagere(app, identifiant, nom):
    # Id de l'étagère, ou None
    for etagere in cave_de(app, identifiant).etageres:
        if etagere.nom == nom:
            return etagere.id
    return None


def creer_etagere(client, nom="E1", capacite="10"):
    return client.post("/etageres", data={"nom": nom, "capacite": capacite}, follow_redirects=True)


def creer_vin(client, nom="Cabernet Sauvignon", millesime="1967"):
    # Crée ou retrouve un vin, renvoie son id
    reponse = client.post("/vins/nouveau", data={
        "domaine": "Château Montelena", "nom": nom, "type": "rouge",
        "millesime": millesime, "region": "Californie"})
    # redirection vers /vins/<id>
    return int(reponse.headers["Location"].split("/")[-1])


def creer_vin_complet(client, domaine, nom, type_vin, millesime, region):
    # Comme creer_vin, avec tous les champs
    reponse = client.post("/vins/nouveau", data={
        "domaine": domaine, "nom": nom, "type": type_vin, "millesime": millesime, "region": region})
    return int(reponse.headers["Location"].split("/")[-1])


def ajouter_bouteilles(client, vin_id, etagere_id, quantite, prix="20"):
    return client.post(f"/vins/{vin_id}/ajouter", follow_redirects=True,
                       data={"etagere": etagere_id, "quantite": quantite, "prix": prix})
