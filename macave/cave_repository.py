from datetime import date, datetime

from macave.bouteille import Bouteille
from macave.cave_privee import CavePrivee
from macave.enums import StatutBouteille
from macave.etagere import Etagere
from macave.evaluation import Evaluation
from macave.vin_repository import vin_depuis_ligne


def date_en_texte(une_date):
    # Date au format AAAA-MM-JJ, ou None
    if une_date is None:
        return None
    return une_date.isoformat()


class CaveRepository:
    # Cave d'un utilisateur ; le commit est fait par le service

    def __init__(self, connexion):
        self.connexion = connexion

    # Cave

    def creer(self, utilisateur_id: int) -> None:
        self.connexion.execute("INSERT INTO caves (utilisateur_id) VALUES (?)", (utilisateur_id,))

    def charger(self, utilisateur):
        # Recharge la cave complète, ou None si elle n'existe pas
        ligne = self.connexion.execute(
            "SELECT id FROM caves WHERE utilisateur_id = ?", (utilisateur.id,)
        ).fetchone()
        if ligne is None:
            return None
        cave = CavePrivee(utilisateur, ligne["id"])

        # 1. Les étagères
        lignes_etageres = self.connexion.execute(
            "SELECT * FROM etageres WHERE cave_id = ? ORDER BY nom", (cave.id,)
        ).fetchall()
        etageres = {}
        for ligne_etagere in lignes_etageres:
            etagere = Etagere(ligne_etagere["nom"], ligne_etagere["capacite_max"], ligne_etagere["id"])
            cave.etageres.append(etagere)
            etageres[etagere.id] = etagere

        # 2. Les vins, un seul objet par référence
        lignes_vins = self.connexion.execute(
            "SELECT * FROM vins WHERE id IN (SELECT vin_id FROM bouteilles WHERE cave_id = ?)",
            (cave.id,)
        ).fetchall()
        vins = {}
        for ligne_vin in lignes_vins:
            vins[ligne_vin["id"]] = vin_depuis_ligne(ligne_vin)

        # 3. Les bouteilles (en stock et archivées)
        lignes_bouteilles = self.connexion.execute(
            "SELECT * FROM bouteilles WHERE cave_id = ? ORDER BY id", (cave.id,)
        ).fetchall()
        bouteilles = {}
        for ligne_bouteille in lignes_bouteilles:
            bouteille = Bouteille(vins[ligne_bouteille["vin_id"]], cave, ligne_bouteille["prix_achat"],
                                  date.fromisoformat(ligne_bouteille["date_ajout"]), ligne_bouteille["id"])
            if ligne_bouteille["statut"] == "archivee":
                bouteille.statut = StatutBouteille.ARCHIVEE
                bouteille.date_sortie = date.fromisoformat(ligne_bouteille["date_sortie"])
            else:
                # en stock : rangée sur son étagère
                etageres[ligne_bouteille["etagere_id"]].accueillir([bouteille])
            cave.bouteilles.append(bouteille)
            bouteilles[bouteille.id] = bouteille

        # 4. Les évaluations des bouteilles archivées
        lignes_evaluations = self.connexion.execute(
            "SELECT * FROM evaluations WHERE bouteille_id IN"
            " (SELECT id FROM bouteilles WHERE cave_id = ?)", (cave.id,)
        ).fetchall()
        for ligne_evaluation in lignes_evaluations:
            bouteille = bouteilles[ligne_evaluation["bouteille_id"]]
            evaluation = Evaluation(utilisateur, bouteille.vin, bouteille, ligne_evaluation["note"],
                                    ligne_evaluation["commentaire"], ligne_evaluation["id"])
            evaluation.date = datetime.fromisoformat(ligne_evaluation["date"])
            bouteille.evaluation = evaluation

        return cave

    # Étagères

    def inserer_etagere(self, cave, etagere) -> None:
        curseur = self.connexion.execute(
            "INSERT INTO etageres (cave_id, nom, capacite_max) VALUES (?, ?, ?)",
            (cave.id, etagere.nom, etagere.capacite_max),
        )
        etagere.id = curseur.lastrowid

    def modifier_etagere(self, etagere) -> None:
        self.connexion.execute(
            "UPDATE etageres SET nom = ?, capacite_max = ? WHERE id = ?",
            (etagere.nom, etagere.capacite_max, etagere.id),
        )

    def supprimer_etagere(self, etagere) -> None:
        self.connexion.execute("DELETE FROM etageres WHERE id = ?", (etagere.id,))

    # Bouteilles

    def inserer_bouteille(self, cave, bouteille) -> None:
        # toujours rangée sur une étagère à l'ajout
        curseur = self.connexion.execute(
            "INSERT INTO bouteilles (vin_id, cave_id, etagere_id, prix_achat, date_ajout, statut,"
            " date_sortie) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (bouteille.vin.id, cave.id, bouteille.etagere.id, bouteille.prix_achat,
             date_en_texte(bouteille.date_ajout), bouteille.statut.value,
             date_en_texte(bouteille.date_sortie)),
        )
        bouteille.id = curseur.lastrowid

    def modifier_bouteille(self, bouteille) -> None:
        # Enregistre étagère, prix, dates et statut
        if bouteille.etagere is None:
            etagere_id = None
        else:
            etagere_id = bouteille.etagere.id
        self.connexion.execute(
            "UPDATE bouteilles SET etagere_id = ?, prix_achat = ?, date_ajout = ?, statut = ?,"
            " date_sortie = ? WHERE id = ?",
            (etagere_id, bouteille.prix_achat, date_en_texte(bouteille.date_ajout),
             bouteille.statut.value, date_en_texte(bouteille.date_sortie), bouteille.id),
        )

    def supprimer_bouteille(self, bouteille) -> None:
        self.connexion.execute("DELETE FROM bouteilles WHERE id = ?", (bouteille.id,))

    # Évaluations

    def inserer_evaluation(self, evaluation) -> None:
        curseur = self.connexion.execute(
            "INSERT INTO evaluations (bouteille_id, auteur_id, vin_id, note, commentaire, date)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (evaluation.bouteille.id, evaluation.auteur.id, evaluation.vin.id, evaluation.note,
             evaluation.commentaire, evaluation.date.isoformat()),
        )
        evaluation.id = curseur.lastrowid

    def modifier_evaluation(self, evaluation) -> None:
        self.connexion.execute(
            "UPDATE evaluations SET note = ?, commentaire = ? WHERE id = ?",
            (evaluation.note, evaluation.commentaire, evaluation.id),
        )
