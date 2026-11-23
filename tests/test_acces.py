# Contrôle d'accès côté serveur (R1)
import re

from macave.db import get_db
from tests.aides import client_connecte

# pages publiques
PAGES_PUBLIQUES = ["accueil", "auth.connexion", "auth.inscription", "auth.deconnexion", "static"]


def test_toutes_les_pages_privees_renvoient_vers_la_connexion(app, client):
    # Parcourt toutes les routes : une page oubliée fait échouer le test
    nb_testees = 0
    for regle in app.url_map.iter_rules():
        if regle.endpoint in PAGES_PUBLIQUES:
            continue
        # remplace chaque <...> par 1
        adresse = re.sub(r"<[^>]+>", "1", regle.rule)
        for methode in ("GET", "POST"):
            if methode in regle.methods:
                reponse = client.open(adresse, method=methode)
                assert reponse.status_code == 302, regle.endpoint + " " + methode
                assert reponse.headers["Location"] == "/connexion", regle.endpoint + " " + methode
                nb_testees += 1
    assert nb_testees >= 20   # 20 pages privées aujourd'hui


def test_une_session_dont_le_compte_n_existe_plus_est_nettoyee(app):
    alice = client_connecte(app, "alice")
    with app.app_context():
        connexion = get_db()
        connexion.execute("DELETE FROM utilisateurs")   # le compte disparaît de la base
        connexion.commit()
    reponse = alice.get("/etageres")
    assert reponse.status_code == 302 and reponse.headers["Location"] == "/connexion"
    # session vidée : il faut se reconnecter
    assert alice.get("/etageres").headers["Location"] == "/connexion"
