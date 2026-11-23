from datetime import datetime

from macave.enums import TypeVin
from macave.vin import Vin


def vin_depuis_ligne(ligne) -> Vin:
    # Ligne de la table vins vers un objet Vin
    return Vin(
        ligne["domaine"], ligne["nom"], TypeVin(ligne["type"]), ligne["millesime"], ligne["region"],
        ligne["description"], ligne["photo_etiquette"], ligne["id"],
    )


class VinRepository:
    # Catalogue partagé. Pas de commit ici

    def __init__(self, connexion):
        self.connexion = connexion

    def trouver(self, id: int):
        ligne = self.connexion.execute("SELECT * FROM vins WHERE id = ?", (id,)).fetchone()
        if ligne is None:
            return None
        return vin_depuis_ligne(ligne)

    def lister(self) -> list:
        # Chaque vin avec sa moyenne (None sans évaluation)
        # LEFT JOIN : garde aussi les vins sans évaluation
        lignes = self.connexion.execute(
            "SELECT v.*, AVG(e.note) AS moyenne, COUNT(e.id) AS nb_evaluations"
            " FROM vins v LEFT JOIN evaluations e ON e.vin_id = v.id"
            " GROUP BY v.id ORDER BY v.domaine, v.nom, v.millesime"
        ).fetchall()
        resultat = []
        for ligne in lignes:
            resultat.append({"vin": vin_depuis_ligne(ligne), "moyenne": ligne["moyenne"],
                             "nb_evaluations": ligne["nb_evaluations"]})
        return resultat

    def moyennes_par_vin(self) -> dict:
        # Seulement les vins évalués
        lignes = self.connexion.execute(
            "SELECT vin_id, AVG(note) AS moyenne, COUNT(*) AS nombre FROM evaluations GROUP BY vin_id"
        ).fetchall()
        moyennes = {}
        for ligne in lignes:
            moyennes[ligne["vin_id"]] = (ligne["moyenne"], ligne["nombre"])
        return moyennes

    def note_moyenne(self, vin_id: int):
        # AVG recalculé à chaque appel ; None sans évaluation
        ligne = self.connexion.execute(
            "SELECT AVG(note) AS moyenne, COUNT(*) AS nombre FROM evaluations WHERE vin_id = ?",
            (vin_id,),
        ).fetchone()
        return ligne["moyenne"], ligne["nombre"]

    def evaluations_du_vin(self, vin_id: int) -> list:
        # Auteur, note, commentaire, date : rien sur sa cave
        lignes = self.connexion.execute(
            "SELECT u.identifiant AS auteur, e.note, e.commentaire, e.date"
            " FROM evaluations e JOIN utilisateurs u ON u.id = e.auteur_id"
            " WHERE e.vin_id = ? ORDER BY e.date DESC",
            (vin_id,),
        ).fetchall()
        resultat = []
        for ligne in lignes:
            resultat.append({"auteur": ligne["auteur"], "note": ligne["note"],
                             "commentaire": ligne["commentaire"],
                             "date": datetime.fromisoformat(ligne["date"])})
        return resultat

    def trouver_ou_creer(self, vin: Vin):
        # Cherche par clé d'identité, sinon crée. Renvoie (vin, cree)
        ligne = self.connexion.execute(
            "SELECT * FROM vins WHERE cle_identite = ?", (vin.cle_identite(),)
        ).fetchone()
        if ligne is not None:
            return vin_depuis_ligne(ligne), False

        curseur = self.connexion.execute(
            "INSERT INTO vins (domaine, nom, type, millesime, region, description, photo_etiquette,"
            " cle_identite) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (vin.domaine, vin.nom, vin.type.value, vin.millesime, vin.region,
             vin.description, vin.photo_etiquette, vin.cle_identite()),
        )
        vin.id = curseur.lastrowid
        return vin, True
