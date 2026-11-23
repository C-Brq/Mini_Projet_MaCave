# Scénarios du sujet, par les pages
import pytest

from macave.catalogue_service import CatalogueService
from macave.db import get_db
from tests.aides import (ajouter_bouteilles, cave_de, client_connecte, creer_etagere, creer_vin,
                         id_etagere, page)


@pytest.fixture
def alice(app):
    return client_connecte(app, "alice")


@pytest.fixture
def bob(app):
    return client_connecte(app, "bob")


def nb_vins_du_catalogue(app):
    with app.app_context():
        return len(CatalogueService(get_db()).lister_vins())


def ids_bouteilles(app, identifiant):
    return [bouteille.id for bouteille in cave_de(app, identifiant).bouteilles]


def alice_avec_cinq_bouteilles(app, alice):
    # E1 (capacité 10) avec 5 bouteilles identiques
    creer_etagere(alice, "E1", "10")
    vin_id = creer_vin(alice)
    etagere_id = id_etagere(app, "alice", "E1")
    ajouter_bouteilles(alice, vin_id, etagere_id, 5)
    return vin_id, etagere_id


def archiver(client, bouteille_id, note, commentaire=""):
    return client.post(f"/bouteilles/{bouteille_id}/archiver", follow_redirects=True,
                       data={"note": note, "commentaire": commentaire, "date_sortie": ""})


# Accès

@pytest.mark.parametrize("url", ["/vins", "/vins/nouveau", "/vins/1", "/bouteilles", "/bouteilles/1", "/historique"])
def test_pages_protegees_quand_on_n_est_pas_connecte(client, url):
    reponse = client.get(url)
    assert reponse.status_code == 302 and reponse.headers["Location"] == "/connexion"


@pytest.mark.parametrize("url", [
    "/vins/nouveau", "/vins/1/ajouter", "/bouteilles/1/modifier", "/bouteilles/1/deplacer",
    "/bouteilles/1/retirer", "/bouteilles/1/archiver", "/bouteilles/1/evaluation"])
def test_envois_de_formulaires_refuses_quand_on_n_est_pas_connecte(client, url):
    reponse = client.post(url, data={"nom": "x"})
    assert reponse.status_code == 302 and reponse.headers["Location"] == "/connexion"


# Catalogue

def test_creer_un_vin_ouvre_sa_fiche_avec_non_evalue(app, alice):
    vin_id = creer_vin(alice)
    contenu = page(alice.get(f"/vins/{vin_id}"))
    assert "Cabernet Sauvignon" in contenu and "Château Montelena" in contenu and "1967" in contenu
    assert "Non évalué" in contenu and "0 / 20" not in contenu   # « Non évalué » et pas zéro


def test_le_meme_vin_ecrit_autrement_n_est_pas_cree_deux_fois(app, alice):
    premier = creer_vin(alice)
    reponse = alice.post("/vins/nouveau", data={
        "domaine": "  château   MONTELENA ", "nom": "cabernet sauvignon", "type": "rouge",
        "millesime": "1967", "region": " californie"}, follow_redirects=True)
    assert "existe déjà" in page(reponse)
    assert nb_vins_du_catalogue(app) == 1
    assert creer_vin(alice) == premier


def test_un_millesime_different_est_un_autre_vin(app, alice):
    assert creer_vin(alice, millesime="1967") != creer_vin(alice, millesime="1968")
    assert nb_vins_du_catalogue(app) == 2


@pytest.mark.parametrize("modifs, message", [
    ({"millesime": "abc"}, "nombre entier"),
    ({"millesime": "0"}, "strictement positif"),
    ({"millesime": "1" + "0" * 20}, "strictement positif"),   # trop grand pour SQLite : refusé sans erreur 500
    ({"nom": "  "}, "ne peut pas être vide"),
    ({"nom": "x" * 101}, "ne peut pas dépasser 100 caractères"),
    ({"description": "x" * 1001}, "ne peut pas dépasser 1000 caractères"),
    ({"domaine": "A|B"}, "Le caractère |"),
    ({"type": "inconnu"}, "Le type du vin"),
    ({"photo_etiquette": "javascript:alert(1)"}, "adresse web"),
])
def test_vin_invalide_refuse(app, alice, modifs, message):
    donnees = {"domaine": "D", "nom": "N", "type": "rouge", "millesime": "2000", "region": "R",
               "photo_etiquette": ""}
    donnees.update(modifs)
    reponse = alice.post("/vins/nouveau", data=donnees)
    assert reponse.status_code == 200 and message in page(reponse)  # on reste sur le formulaire
    assert nb_vins_du_catalogue(app) == 0


def test_le_formulaire_garde_les_valeurs_saisies_en_cas_d_erreur(alice):
    reponse = alice.post("/vins/nouveau", data={
        "domaine": "Mon domaine", "nom": "Ma cuvée", "type": "blanc", "millesime": "abc", "region": "Alsace"})
    contenu = page(reponse)
    assert 'value="Mon domaine"' in contenu and 'value="Alsace"' in contenu


def test_vin_inexistant_donne_404(alice):
    assert alice.get("/vins/9999").status_code == 404


def test_le_catalogue_liste_les_vins(alice):
    creer_vin(alice)
    assert "Cabernet Sauvignon" in page(alice.get("/vins"))


# Ajout de bouteilles

def test_ajouter_5_bouteilles_identiques_donne_5_exemplaires_et_une_seule_reference(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    cave = cave_de(app, "alice")
    assert cave.nb_bouteilles() == 5 and cave.nb_references() == 1
    assert nb_vins_du_catalogue(app) == 1


def test_ajouter_6_bouteilles_a_une_etagere_a_5_sur_10_est_refuse_sans_ajout_partiel(app, alice):
    vin_id, etagere_id = alice_avec_cinq_bouteilles(app, alice)
    reponse = ajouter_bouteilles(alice, vin_id, etagere_id, 6)
    assert "Capacité de l" in page(reponse)
    cave = cave_de(app, "alice")
    assert cave.nb_bouteilles() == 5 and cave.etageres[0].occupation == 5


@pytest.mark.parametrize("quantite, prix, message", [
    ("0", "20", "strictement positif"),
    ("99999999999999999999", "20", "strictement positif"),
    ("abc", "20", "nombre entier"),
    ("2", "abc", "doit être un nombre"),
    ("2", "-5", "compris entre 0 et 1 000 000"),
    ("2", "", "doit être un nombre"),
])
def test_ajout_invalide_refuse(app, alice, quantite, prix, message):
    creer_etagere(alice, "E1", "10")
    vin_id = creer_vin(alice)
    reponse = ajouter_bouteilles(alice, vin_id, id_etagere(app, "alice", "E1"), quantite, prix)
    assert message in page(reponse)
    assert cave_de(app, "alice").bouteilles == []


def test_le_prix_peut_s_ecrire_avec_une_virgule(app, alice):
    creer_etagere(alice, "E1", "10")
    ajouter_bouteilles(alice, creer_vin(alice), id_etagere(app, "alice", "E1"), 1, "12,50")
    assert cave_de(app, "alice").bouteilles[0].prix_achat == 12.5


def test_sans_etagere_la_fiche_du_vin_propose_d_en_creer_une(alice):
    contenu = page(alice.get(f"/vins/{creer_vin(alice)}"))
    assert "pas encore d" in contenu and "Créez-en une" in contenu


# Déplacement, retrait, modification

def test_deplacer_une_bouteille_met_a_jour_l_occupation_des_deux_etageres(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    creer_etagere(alice, "E2", "10")
    bouteille_id = ids_bouteilles(app, "alice")[0]
    reponse = alice.post(f"/bouteilles/{bouteille_id}/deplacer", follow_redirects=True,
                         data={"etagere": id_etagere(app, "alice", "E2")})
    assert "a été déplacée" in page(reponse)
    etageres = cave_de(app, "alice").etageres
    assert [(e.nom, e.occupation) for e in etageres] == [("E1", 4), ("E2", 1)]


def test_deplacer_vers_une_etagere_pleine_est_refuse(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    creer_etagere(alice, "Petite", "1")
    ids = ids_bouteilles(app, "alice")
    petite = id_etagere(app, "alice", "Petite")
    alice.post(f"/bouteilles/{ids[0]}/deplacer", data={"etagere": petite})
    reponse = alice.post(f"/bouteilles/{ids[1]}/deplacer", data={"etagere": petite}, follow_redirects=True)
    assert "Capacité de l" in page(reponse)
    assert [(e.nom, e.occupation) for e in cave_de(app, "alice").etageres] == [("E1", 4), ("Petite", 1)]


def test_retirer_definitivement_un_exemplaire_garde_le_vin_au_catalogue(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    bouteille_id = ids_bouteilles(app, "alice")[0]
    reponse = alice.post(f"/bouteilles/{bouteille_id}/retirer", follow_redirects=True)
    assert "a été retirée" in page(reponse)
    cave = cave_de(app, "alice")
    assert cave.nb_bouteilles() == 4 and cave.historique() == []
    assert nb_vins_du_catalogue(app) == 1


def test_modifier_le_prix_et_la_date_d_une_bouteille(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    bouteille_id = ids_bouteilles(app, "alice")[0]
    reponse = alice.post(f"/bouteilles/{bouteille_id}/modifier", follow_redirects=True,
                         data={"prix": "35,5", "date_ajout": "2024-05-17"})
    assert "a été modifiée" in page(reponse)
    bouteille = cave_de(app, "alice").bouteilles[0]
    assert bouteille.prix_achat == 35.5 and bouteille.date_ajout.isoformat() == "2024-05-17"


@pytest.mark.parametrize("prix, date_ajout, message", [
    ("abc", "2024-05-17", "doit être un nombre"),
    ("-1", "2024-05-17", "compris entre 0 et 1 000 000"),
    ("10", "17/05/2024", "pas une date valide"),
    ("10", "", "pas une date valide"),
    ("10", "2999-01-01", "dans le futur"),
])
def test_modification_invalide_refusee(app, alice, prix, date_ajout, message):
    alice_avec_cinq_bouteilles(app, alice)
    bouteille_id = ids_bouteilles(app, "alice")[0]
    reponse = alice.post(f"/bouteilles/{bouteille_id}/modifier", follow_redirects=True,
                         data={"prix": prix, "date_ajout": date_ajout})
    assert message in page(reponse)
    assert cave_de(app, "alice").bouteilles[0].prix_achat == 20


# Archivage et évaluations

def test_archiver_un_exemplaire_parmi_5_laisse_4_en_stock_et_1_dans_l_historique(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    bouteille_id = ids_bouteilles(app, "alice")[0]
    reponse = archiver(alice, bouteille_id, "16", "Très bon")
    assert "archivée avec son évaluation" in page(reponse)
    cave = cave_de(app, "alice")
    assert cave.nb_bouteilles() == 4 and len(cave.historique()) == 1
    assert cave.etageres[0].occupation == 4  # l'exemplaire archivé n'occupe plus de place
    historique = page(alice.get("/historique"))
    assert "16 / 20" in historique and "Très bon" in historique


def test_archiver_avec_une_date_de_degustation_choisie(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    bouteille_id = ids_bouteilles(app, "alice")[0]
    # date d'ajout reculée pour tester une date passée
    alice.post(f"/bouteilles/{bouteille_id}/modifier", data={"prix": "20", "date_ajout": "2025-01-01"})
    alice.post(f"/bouteilles/{bouteille_id}/archiver", data={"note": "15", "date_sortie": "2025-12-24"})
    assert cave_de(app, "alice").historique()[0].date_sortie.isoformat() == "2025-12-24"


@pytest.mark.parametrize("date_sortie, message", [
    ("2000-01-01", "avant la date d"),        # avant la date d'ajout (aujourd'hui)
    ("2999-01-01", "dans le futur"),
])
def test_archiver_avec_une_date_incoherente_est_refuse(app, alice, date_sortie, message):
    alice_avec_cinq_bouteilles(app, alice)
    bouteille_id = ids_bouteilles(app, "alice")[0]
    reponse = alice.post(f"/bouteilles/{bouteille_id}/archiver", follow_redirects=True,
                         data={"note": "15", "date_sortie": date_sortie})
    assert message in page(reponse)
    cave = cave_de(app, "alice")
    assert cave.nb_bouteilles() == 5 and cave.historique() == []   # rien n'a été archivé ni évalué


def test_les_dates_de_la_fiche_sont_des_champs_de_date(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    contenu = page(alice.get(f"/bouteilles/{ids_bouteilles(app, 'alice')[0]}"))
    assert 'type="date" id="date_ajout"' in contenu and 'type="date" id="date_sortie"' in contenu


def test_retirer_une_bouteille_demande_une_confirmation(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    contenu = page(alice.get(f"/bouteilles/{ids_bouteilles(app, 'alice')[0]}"))
    assert "confirm(" in contenu


def test_archiver_avec_une_date_invalide_est_refuse(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    bouteille_id = ids_bouteilles(app, "alice")[0]
    reponse = alice.post(f"/bouteilles/{bouteille_id}/archiver", follow_redirects=True,
                         data={"note": "15", "date_sortie": "24/12/2025"})
    assert "pas une date valide" in page(reponse)
    assert cave_de(app, "alice").nb_bouteilles() == 5


@pytest.mark.parametrize("note", ["21", "-1", "abc", ""])
def test_note_invalide_refusee_et_la_bouteille_reste_en_stock(app, alice, note):
    alice_avec_cinq_bouteilles(app, alice)
    bouteille_id = ids_bouteilles(app, "alice")[0]
    archiver(alice, bouteille_id, note)
    assert cave_de(app, "alice").nb_bouteilles() == 5


def test_une_bouteille_archivee_ne_peut_etre_ni_archivee_ni_retiree_une_seconde_fois(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    bouteille_id = ids_bouteilles(app, "alice")[0]
    archiver(alice, bouteille_id, "14")
    assert "déjà archivée" in page(archiver(alice, bouteille_id, "18"))
    reponse = alice.post(f"/bouteilles/{bouteille_id}/retirer", follow_redirects=True)
    assert "ne peut pas être retirée" in page(reponse)
    cave = cave_de(app, "alice")
    assert len(cave.historique()) == 1 and cave.historique()[0].evaluation.note == 14


def test_les_notes_16_12_17_donnent_une_moyenne_communautaire_de_15_sur_20(app, alice):
    vin_id, _ = alice_avec_cinq_bouteilles(app, alice)
    ids = ids_bouteilles(app, "alice")
    for bouteille_id, note in zip(ids, ("16", "12", "17")):
        archiver(alice, bouteille_id, note)
    contenu = page(alice.get(f"/vins/{vin_id}"))
    assert "15 / 20" in contenu and "3 évaluations" in contenu


def test_modifier_une_note_est_repercute_dans_la_moyenne(app, alice):
    vin_id, _ = alice_avec_cinq_bouteilles(app, alice)
    ids = ids_bouteilles(app, "alice")
    for bouteille_id, note in zip(ids, ("16", "12", "17")):
        archiver(alice, bouteille_id, note)
    reponse = alice.post(f"/bouteilles/{ids[0]}/evaluation", follow_redirects=True,
                         data={"note": "10", "commentaire": "Finalement bof"})
    assert "évaluation a été modifiée" in page(reponse)
    assert "13 / 20" in page(alice.get(f"/vins/{vin_id}"))   # (10 + 12 + 17) / 3 = 13


def test_modification_d_une_evaluation_avec_une_note_invalide_refusee(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    bouteille_id = ids_bouteilles(app, "alice")[0]
    archiver(alice, bouteille_id, "16")
    alice.post(f"/bouteilles/{bouteille_id}/evaluation", data={"note": "25"})
    assert cave_de(app, "alice").historique()[0].evaluation.note == 16


def test_on_ne_peut_pas_evaluer_une_bouteille_encore_en_stock(app, alice):
    alice_avec_cinq_bouteilles(app, alice)
    bouteille_id = ids_bouteilles(app, "alice")[0]
    assert alice.post(f"/bouteilles/{bouteille_id}/evaluation", data={"note": "10"}).status_code == 404


def test_les_evaluations_de_plusieurs_degustations_du_meme_utilisateur_comptent_chacune(app, alice):
    # R10 : chaque dégustation a le même poids
    vin_id, _ = alice_avec_cinq_bouteilles(app, alice)
    ids = ids_bouteilles(app, "alice")
    archiver(alice, ids[0], "20")
    archiver(alice, ids[1], "10")
    assert "15 / 20" in page(alice.get(f"/vins/{vin_id}"))


# Données partagées et privées

def test_une_reference_partagee_montre_les_evaluations_aux_deux_comptes(app, alice, bob):
    vin_id, _ = alice_avec_cinq_bouteilles(app, alice)
    archiver(alice, ids_bouteilles(app, "alice")[0], "16", "Excellent millésime")
    for client in (alice, bob):
        contenu = page(client.get(f"/vins/{vin_id}"))
        assert "alice" in contenu and "16 / 20" in contenu and "Excellent millésime" in contenu


def test_publier_une_evaluation_ne_revele_rien_de_la_cave_de_son_auteur(app, alice, bob):
    creer_etagere(alice, "Etagere-secrete", "10")
    vin_id = creer_vin(alice)
    ajouter_bouteilles(alice, vin_id, id_etagere(app, "alice", "Etagere-secrete"), 3, "199")
    archiver(alice, ids_bouteilles(app, "alice")[0], "16")
    contenu_de_bob = page(bob.get(f"/vins/{vin_id}"))
    assert "16 / 20" in contenu_de_bob                      # l'évaluation est publique...
    assert "Etagere-secrete" not in contenu_de_bob          # ...mais pas la cave
    assert "199" not in contenu_de_bob                      # ni le prix payé
    assert "Vous ne possédez aucun exemplaire" in contenu_de_bob


def test_les_notes_et_commentaires_sont_echappes(app, alice):
    vin_id, _ = alice_avec_cinq_bouteilles(app, alice)
    archiver(alice, ids_bouteilles(app, "alice")[0], "10", "<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in page(alice.get(f"/vins/{vin_id}"))


def test_le_stock_prive_d_un_autre_compte_est_inaccessible(app, alice, bob):
    alice_avec_cinq_bouteilles(app, alice)
    assert "Vous n'avez aucune bouteille" in page(bob.get("/bouteilles")).replace("&#39;", "'")
    assert "Cabernet" not in page(bob.get("/bouteilles"))
    assert "Cabernet" not in page(bob.get("/historique"))


def test_acces_direct_aux_bouteilles_d_un_autre_compte_refuse(app, alice, bob):
    vin_id, etagere_id = alice_avec_cinq_bouteilles(app, alice)
    archiver(alice, ids_bouteilles(app, "alice")[1], "12")
    en_stock, archivee = ids_bouteilles(app, "alice")[0], ids_bouteilles(app, "alice")[1]
    creer_etagere(bob, "B1", "10")
    etagere_de_bob = id_etagere(app, "bob", "B1")

    assert bob.get(f"/bouteilles/{en_stock}").status_code == 404
    assert bob.post(f"/bouteilles/{en_stock}/modifier", data={"prix": "1", "date_ajout": "2024-01-01"}).status_code == 404
    assert bob.post(f"/bouteilles/{en_stock}/deplacer", data={"etagere": etagere_de_bob}).status_code == 404
    assert bob.post(f"/bouteilles/{en_stock}/archiver", data={"note": "1"}).status_code == 404
    assert bob.post(f"/bouteilles/{en_stock}/retirer").status_code == 404
    assert bob.post(f"/bouteilles/{archivee}/evaluation", data={"note": "20"}).status_code == 404
    # Bob ne peut pas utiliser l'étagère d'Alice
    assert bob.post(f"/vins/{vin_id}/ajouter", data={"etagere": etagere_id, "quantite": "1", "prix": "1"}).status_code == 404

    # rien n'a changé chez Alice
    cave = cave_de(app, "alice")
    assert cave.nb_bouteilles() == 4 and len(cave.historique()) == 1
    assert cave.historique()[0].evaluation.note == 12 and cave.valeur_stock() == 80
    assert cave_de(app, "bob").bouteilles == []
