# Règles métier sans Flask ni base, d'après les scénarios du sujet
from datetime import date, timedelta

import pytest

from macave.cave_privee import CavePrivee
from macave.enums import StatutBouteille, TypeVin
from macave.utilisateur import Utilisateur
from macave.vin import Vin


@pytest.fixture
def alice():
    return Utilisateur("alice", "alice@example.fr", "motdepasse1")


@pytest.fixture
def cave(alice):
    return CavePrivee(alice)


@pytest.fixture
def vin():
    return Vin("Château Montelena", "Cabernet Sauvignon", TypeVin.ROUGE, 1967, "Californie")


def ajouter(cave, etagere, vin, quantite):
    # Bouteilles à 20 € pièce
    return cave.ajouter_bouteilles(vin, etagere, quantite, 20)


# Étagères

def test_etagere_de_capacite_10_est_vide_au_depart(cave):
    etagere = cave.creer_etagere("E1", 10)
    assert (etagere.occupation, etagere.capacite_max) == (0, 10)


def test_capacite_jamais_inferieure_a_l_occupation(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    ajouter(cave, etagere, vin, 5)
    with pytest.raises(ValueError):
        etagere.modifier_capacite(4)
    etagere.modifier_capacite(5)


# trop grand pour SQLite : refusé avant la base
@pytest.mark.parametrize("capacite", [0, -5, 2.5, "10", True, 1000001, 10 ** 20])
def test_capacite_invalide_refusee(cave, capacite):
    with pytest.raises(ValueError):
        cave.creer_etagere("E1", capacite)
    assert cave.etageres == []


def test_noms_d_etagere_uniques_dans_une_cave(cave):
    cave.creer_etagere("E1", 10)
    with pytest.raises(ValueError):
        cave.creer_etagere("E1", 5)


def test_noms_d_etagere_uniques_meme_avec_une_autre_casse_ou_des_espaces(cave):
    cave.creer_etagere("Cave du fond", 10)
    with pytest.raises(ValueError):
        cave.creer_etagere("  cave   DU FOND ", 5)
    assert len(cave.etageres) == 1


def test_nom_d_etagere_vide_refuse(cave):
    with pytest.raises(ValueError):
        cave.creer_etagere("   ", 10)


def test_suppression_d_une_etagere_non_vide_refusee(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    ajouter(cave, etagere, vin, 1)
    with pytest.raises(ValueError):
        cave.supprimer_etagere(etagere)


# Ajout de bouteilles

def test_cinq_bouteilles_identiques_sont_cinq_exemplaires_d_une_reference(cave, vin):
    ajouter(cave, cave.creer_etagere("E1", 10), vin, 5)
    assert cave.nb_bouteilles() == 5 and cave.nb_references() == 1


def test_ajout_depassant_la_capacite_refuse_sans_ajout_partiel(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    ajouter(cave, etagere, vin, 5)
    with pytest.raises(ValueError):
        ajouter(cave, etagere, vin, 6)
    assert etagere.occupation == 5


def test_ajout_refuse_ne_laisse_aucune_trace_dans_la_cave(cave, vin):
    # la cave reste intacte aussi
    etagere = cave.creer_etagere("E1", 10)
    ajouter(cave, etagere, vin, 5)
    with pytest.raises(ValueError):
        ajouter(cave, etagere, vin, 6)
    assert cave.nb_bouteilles() == 5
    assert len(cave.bouteilles) == 5
    assert cave.valeur_stock() == 100


@pytest.mark.parametrize("quantite", [0, -1, 2.5, "3", True])
def test_quantite_invalide_refusee(cave, vin, quantite):
    etagere = cave.creer_etagere("E1", 10)
    with pytest.raises(ValueError):
        ajouter(cave, etagere, vin, quantite)
    assert cave.bouteilles == [] and etagere.occupation == 0


@pytest.mark.parametrize("prix", [-1, "abc", None, True, float("nan")])
def test_prix_invalide_refuse_sans_rien_ajouter(cave, vin, prix):
    etagere = cave.creer_etagere("E1", 10)
    with pytest.raises(ValueError):
        cave.ajouter_bouteilles(vin, etagere, 3, prix)
    assert cave.bouteilles == [] and etagere.occupation == 0


def test_ajout_sur_l_etagere_d_une_autre_cave_refuse(cave, vin):
    cave_de_bob = CavePrivee(Utilisateur("bob", "bob@example.fr", "motdepasse2"))
    etagere_de_bob = cave_de_bob.creer_etagere("E1", 10)
    with pytest.raises(ValueError):
        ajouter(cave, etagere_de_bob, vin, 2)
    assert etagere_de_bob.occupation == 0 and cave.bouteilles == []


def test_valeur_du_stock_arrondie_au_centime(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    cave.ajouter_bouteilles(vin, etagere, 1, 0.1)
    cave.ajouter_bouteilles(vin, etagere, 1, 0.2)
    assert cave.valeur_stock() == 0.3  # sans arrondi : 0.30000000000000004


# Déplacement

def test_deplacement_met_a_jour_les_deux_etageres(cave, vin):
    e1, e2 = cave.creer_etagere("E1", 10), cave.creer_etagere("E2", 2)
    b = ajouter(cave, e1, vin, 5)
    b[0].deplacer_vers(e2)
    assert (e1.occupation, e2.occupation) == (4, 1)


def test_deplacement_vers_une_etagere_pleine_est_refuse(cave, vin):
    e1, e2 = cave.creer_etagere("E1", 10), cave.creer_etagere("E2", 1)
    b = ajouter(cave, e1, vin, 2)
    b[0].deplacer_vers(e2)
    with pytest.raises(ValueError):
        b[1].deplacer_vers(e2)
    assert (e1.occupation, e2.occupation) == (1, 1)


def test_deplacement_vers_l_etagere_d_une_autre_cave_refuse(cave, vin):
    cave_de_bob = CavePrivee(Utilisateur("bob", "bob@example.fr", "motdepasse2"))
    etagere_de_bob = cave_de_bob.creer_etagere("E1", 10)
    e1 = cave.creer_etagere("E1", 10)
    b = ajouter(cave, e1, vin, 1)
    with pytest.raises(ValueError):
        b[0].deplacer_vers(etagere_de_bob)
    assert b[0].etagere is e1 and etagere_de_bob.occupation == 0


# Retrait et archivage

def test_archiver_un_exemplaire_sur_cinq_en_laisse_quatre_en_stock(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    b = ajouter(cave, etagere, vin, 5)
    b[0].archiver(16)
    assert cave.nb_bouteilles() == 4 and len(cave.historique()) == 1
    assert b[0].statut == StatutBouteille.ARCHIVEE and etagere.occupation == 4


def test_une_bouteille_archivee_ne_peut_plus_etre_archivee_ni_retiree(cave, vin):
    b = ajouter(cave, cave.creer_etagere("E1", 10), vin, 1)
    b[0].archiver(14)
    with pytest.raises(ValueError):
        b[0].archiver(14)
    with pytest.raises(ValueError):
        b[0].retirer()


def test_retrait_definitif_d_un_exemplaire_sur_cinq(cave, vin):
    b = ajouter(cave, cave.creer_etagere("E1", 10), vin, 5)
    b[0].retirer()
    assert cave.nb_bouteilles() == 4 and cave.historique() == []


# Évaluations
# moyenne testée dans test_catalogue_service.py

def test_note_hors_bornes_refusee_sans_rien_modifier(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    b = ajouter(cave, etagere, vin, 1)
    with pytest.raises(ValueError):
        b[0].archiver(21)
    assert b[0].est_en_stock() and etagere.occupation == 1 and b[0].evaluation is None


def test_evaluation_modifiable_par_son_seul_auteur(alice, cave, vin):
    b = ajouter(cave, cave.creer_etagere("E1", 10), vin, 1)
    evaluation = b[0].archiver(10)
    with pytest.raises(PermissionError):
        evaluation.modifier(Utilisateur("bob", "bob@example.fr", "motdepasse2"), 20)
    assert evaluation.note == 10   # la tentative de bob n'a rien changé
    evaluation.modifier(alice, 18)
    assert evaluation.note == 18


def test_commentaire_trop_long_refuse_sans_rien_modifier(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    b = ajouter(cave, etagere, vin, 1)
    with pytest.raises(ValueError):
        b[0].archiver(15, "x" * 1001)
    assert b[0].est_en_stock() and etagere.occupation == 1
    b[0].archiver(15, "x" * 1000)   # 1000 caractères : accepté


# Dates de la bouteille

def test_archiver_avec_une_date_de_degustation_choisie(cave, vin):
    bouteille = ajouter(cave, cave.creer_etagere("E1", 10), vin, 1)[0]
    bouteille.modifier_infos(20, date(2024, 1, 10))
    bouteille.archiver(15, None, date(2024, 6, 1))
    assert bouteille.date_sortie == date(2024, 6, 1)


def test_archiver_le_jour_meme_de_l_ajout_est_accepte(cave, vin):
    bouteille = ajouter(cave, cave.creer_etagere("E1", 10), vin, 1)[0]
    bouteille.archiver(15, None, bouteille.date_ajout)
    assert bouteille.date_sortie == bouteille.date_ajout


def test_date_de_sortie_avant_la_date_d_ajout_refusee_sans_rien_modifier(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    bouteille = ajouter(cave, etagere, vin, 1)[0]   # ajoutée aujourd'hui
    with pytest.raises(ValueError):
        bouteille.archiver(15, None, date(1900, 1, 1))
    assert bouteille.est_en_stock() and etagere.occupation == 1 and bouteille.evaluation is None


def test_date_de_sortie_dans_le_futur_refusee(cave, vin):
    bouteille = ajouter(cave, cave.creer_etagere("E1", 10), vin, 1)[0]
    with pytest.raises(ValueError):
        bouteille.archiver(15, None, date.today() + timedelta(days=1))
    assert bouteille.est_en_stock()


def test_date_de_sortie_qui_n_est_pas_une_date_refusee(cave, vin):
    bouteille = ajouter(cave, cave.creer_etagere("E1", 10), vin, 1)[0]
    with pytest.raises(ValueError):
        bouteille.archiver(15, None, "2024-06-01")   # un texte, pas une date
    assert bouteille.est_en_stock()


def test_date_d_ajout_dans_le_futur_refusee(cave, vin):
    bouteille = ajouter(cave, cave.creer_etagere("E1", 10), vin, 1)[0]
    with pytest.raises(ValueError):
        bouteille.modifier_infos(20, date.today() + timedelta(days=1))
    assert bouteille.date_ajout == date.today()


def test_ajout_avec_une_date_dans_le_futur_refuse_sans_ajout(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    with pytest.raises(ValueError):
        cave.ajouter_bouteilles(vin, etagere, 3, 20, date.today() + timedelta(days=1))
    assert etagere.occupation == 0 and cave.bouteilles == []


# Identité d'une référence de vin

def test_meme_vin_malgre_la_casse_et_les_espaces(vin):
    autre = Vin("  château   MONTELENA ", "cabernet sauvignon", TypeVin.ROUGE, 1967, " CALIFORNIE")
    assert vin.est_le_meme_vin_que(autre)
    assert vin.cle_identite() == autre.cle_identite()


def test_deux_references_equivalentes_ne_comptent_que_pour_une(cave, vin):
    autre = Vin("château montelena", "CABERNET  SAUVIGNON", TypeVin.ROUGE, 1967, "californie")
    etagere = cave.creer_etagere("E1", 10)
    ajouter(cave, etagere, vin, 2)
    ajouter(cave, etagere, autre, 3)
    assert cave.nb_bouteilles() == 5 and cave.nb_references() == 1


def test_vins_differents_si_le_millesime_ou_le_type_change(vin):
    autre_annee = Vin("Château Montelena", "Cabernet Sauvignon", TypeVin.ROUGE, 1968, "Californie")
    autre_type = Vin("Château Montelena", "Cabernet Sauvignon", TypeVin.BLANC, 1967, "Californie")
    assert not vin.est_le_meme_vin_que(autre_annee)
    assert not vin.est_le_meme_vin_que(autre_type)


def test_le_prix_ne_fait_pas_partie_de_l_identite_du_vin(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    cave.ajouter_bouteilles(vin, etagere, 1, 10)
    cave.ajouter_bouteilles(vin, etagere, 1, 50)
    assert cave.nb_references() == 1


@pytest.mark.parametrize("champs", [
    {"domaine": "   "}, {"nom": ""}, {"region": " "},   # textes vides
    {"domaine": 12},                                     # pas un texte
    {"millesime": 0}, {"millesime": "1967"},            # millésime invalide
    {"millesime": 10 ** 20},                             # trop grand pour SQLite
    {"type": "rouge"},                                   # pas un TypeVin
    {"nom": "x" * 101}, {"domaine": "x" * 101}, {"region": "x" * 101},   # textes trop longs
    {"description": "x" * 1001}, {"photo_etiquette": "x" * 501},
    {"domaine": "A|B"}, {"nom": "B|C"}, {"region": "|"},   # « | » sépare les morceaux de la clé d'identité
])
def test_vin_invalide_refuse(champs):
    valeurs = {"domaine": "D", "nom": "N", "type": TypeVin.ROUGE, "millesime": 2000, "region": "R",
               "description": "", "photo_etiquette": ""}
    valeurs.update(champs)
    with pytest.raises(ValueError):
        Vin(valeurs["domaine"], valeurs["nom"], valeurs["type"], valeurs["millesime"], valeurs["region"],
            valeurs["description"], valeurs["photo_etiquette"])


def test_des_textes_de_100_caracteres_sont_acceptes():
    Vin("d" * 100, "n" * 100, TypeVin.ROUGE, 2000, "r" * 100, "x" * 1000, "h" * 500)


# Modifications et propriétaire

def test_modifier_une_etagere_change_le_nom_et_la_capacite(cave):
    etagere = cave.creer_etagere("E1", 10)
    cave.modifier_etagere(etagere, "  Cave   du fond ", 20)
    assert (etagere.nom, etagere.capacite_max) == ("Cave du fond", 20)


def test_modifier_une_etagere_refuse_un_nom_deja_pris_sans_rien_changer(cave):
    cave.creer_etagere("E1", 10)
    e2 = cave.creer_etagere("E2", 10)
    with pytest.raises(ValueError):
        cave.modifier_etagere(e2, "e1", 30)
    assert (e2.nom, e2.capacite_max) == ("E2", 10)


def test_une_etagere_peut_garder_son_nom_en_changeant_de_capacite(cave):
    etagere = cave.creer_etagere("E1", 10)
    cave.modifier_etagere(etagere, "E1", 12)
    assert etagere.capacite_max == 12


def test_modifier_une_etagere_sous_l_occupation_refuse_sans_changer_le_nom(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    ajouter(cave, etagere, vin, 5)
    with pytest.raises(ValueError):
        cave.modifier_etagere(etagere, "Nouveau", 4)
    assert (etagere.nom, etagere.capacite_max) == ("E1", 10)


def test_modifier_le_prix_et_la_date_d_une_bouteille(cave, vin):
    bouteille = ajouter(cave, cave.creer_etagere("E1", 10), vin, 1)[0]
    bouteille.modifier_infos(42.5, date(2023, 1, 31))
    assert bouteille.prix_achat == 42.5 and bouteille.date_ajout == date(2023, 1, 31)


def test_modifier_une_bouteille_avec_des_valeurs_invalides_ne_change_rien(cave, vin):
    bouteille = ajouter(cave, cave.creer_etagere("E1", 10), vin, 1)[0]
    with pytest.raises(ValueError):
        bouteille.modifier_infos(-5, date(2023, 1, 31))
    with pytest.raises(ValueError):
        bouteille.modifier_infos(10, "2023-01-31")  # une date, pas un texte
    assert bouteille.prix_achat == 20 and bouteille.date_ajout == date.today()


def test_une_bouteille_archivee_n_est_plus_modifiable(cave, vin):
    bouteille = ajouter(cave, cave.creer_etagere("E1", 10), vin, 1)[0]
    bouteille.archiver(15)
    with pytest.raises(ValueError):
        bouteille.modifier_infos(10, date.today())


def test_le_proprietaire_est_reconnu_par_son_id_meme_si_l_objet_est_different(cave, alice):
    alice.id = 7
    # même compte rechargé : autre objet, même id
    alice_rechargee = Utilisateur("alice", "alice@example.fr", "motdepasse1", id=7)
    bob = Utilisateur("bob", "bob@example.fr", "motdepasse2", id=8)
    assert cave.appartient_a(alice_rechargee)
    assert not cave.appartient_a(bob)


def test_deux_utilisateurs_sans_id_ne_sont_pas_confondus(cave):
    # deux id None : pas la même personne
    inconnu = Utilisateur("bob", "bob@example.fr", "motdepasse2")
    assert not cave.appartient_a(inconnu)


def test_une_bouteille_archivee_ne_peut_plus_etre_deplacee(cave, vin):
    e1, e2 = cave.creer_etagere("E1", 10), cave.creer_etagere("E2", 10)
    bouteille = ajouter(cave, e1, vin, 1)[0]
    bouteille.archiver(15)
    with pytest.raises(ValueError):
        bouteille.deplacer_vers(e2)
    assert e2.occupation == 0


def test_deplacer_vers_la_meme_etagere_ne_change_rien(cave, vin):
    etagere = cave.creer_etagere("E1", 10)
    bouteille = ajouter(cave, etagere, vin, 3)[0]
    bouteille.deplacer_vers(etagere)
    assert etagere.occupation == 3 and bouteille.etagere is etagere


def test_le_proprietaire_est_reconnu_quand_c_est_le_meme_objet(cave, alice):
    assert cave.appartient_a(alice)


# Indicateurs

def test_occupation_globale_sans_etagere_ne_divise_pas_par_zero(cave):
    assert cave.occupation_globale() is None
