# Textes affichés et fonctionnement hors ligne
import re

from macave.affichage import pourcentage_entier, texte_date, texte_note, texte_pourcentage, texte_prix
from tests.aides import client_connecte, page


# Textes affichés

def test_texte_note():
    assert texte_note(15) == "15 / 20"
    assert texte_note(15.0) == "15 / 20"      # pas de « .0 » inutile
    assert texte_note(15.34) == "15.3 / 20"   # une seule décimale
    assert texte_note(0) == "0 / 20"          # une vraie note de zéro s'affiche...
    assert texte_note(None) == "Non évalué"   # ...mais pas l'absence de note


def test_texte_prix():
    assert texte_prix(20) == "20.00 €"
    assert texte_prix(9.9) == "9.90 €"
    assert texte_prix(0) == "0.00 €"


def test_texte_date():
    from datetime import date
    assert texte_date(date(2025, 12, 31)) == "31/12/2025"
    assert texte_date(date(2026, 1, 5)) == "05/01/2026"


def test_pourcentages():
    assert pourcentage_entier(0.5) == 50
    assert pourcentage_entier(0) == 0
    assert pourcentage_entier(1) == 100
    assert texte_pourcentage(0.364) == "36.4 %"
    assert texte_pourcentage(0.25) == "25.0 %"


# Sans internet

def test_la_feuille_de_style_et_l_image_de_fond_sont_servies_par_l_application(client):
    css = client.get("/static/style.css")
    assert css.status_code == 200 and "text/css" in css.content_type
    fond = client.get("/static/fond.svg")
    assert fond.status_code == 200 and "svg" in fond.content_type
    assert 'url("fond.svg")' in css.get_data(as_text=True)   # le CSS utilise bien l'image locale


def test_les_pages_ne_chargent_rien_depuis_internet(app, client):
    alice = client_connecte(app, "alice")
    adresses = ["/", "/connexion", "/inscription"]
    for adresse in adresses:
        contenu = page(client.get(adresse))
        assert '<link rel="stylesheet" href="/static/style.css">' in contenu
        assert "<script" not in contenu
        # aucune adresse http(s) externe
        assert re.findall(r"https?://", contenu) == [], adresse
    # pareil une fois connecté
    for adresse in ["/", "/etageres", "/bouteilles", "/vins", "/historique", "/profil", "/vins/nouveau"]:
        contenu = page(alice.get(adresse))
        assert re.findall(r"https?://", contenu) == [], adresse


def test_le_css_ne_charge_aucune_ressource_externe(client):
    css = client.get("/static/style.css").get_data(as_text=True)
    assert "http://" not in css and "https://" not in css and "@import" not in css
    assert re.findall(r"url\(([^)]*)\)", css) == ['"fond.svg"']   # la seule ressource : l'image locale
