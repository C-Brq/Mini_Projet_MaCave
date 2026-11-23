from macave.utilisateur import Utilisateur


class UtilisateurRepository:
    # Table utilisateurs

    def __init__(self, connexion):
        self.connexion = connexion

    def inserer(self, utilisateur: Utilisateur) -> None:
        # Pas de commit ; IntegrityError si identifiant ou e-mail déjà pris
        curseur = self.connexion.execute(
            "INSERT INTO utilisateurs (identifiant, email, mot_de_passe_hash) VALUES (?, ?, ?)",
            (utilisateur.identifiant, utilisateur.email, utilisateur.mot_de_passe_hash),
        )
        utilisateur.id = curseur.lastrowid

    def modifier(self, utilisateur: Utilisateur) -> None:
        # Pas de commit ; IntegrityError si l'e-mail est déjà pris
        self.connexion.execute(
            "UPDATE utilisateurs SET email = ?, mot_de_passe_hash = ? WHERE id = ?",
            (utilisateur.email, utilisateur.mot_de_passe_hash, utilisateur.id),
        )

    def trouver(self, id: int):
        return self._un("SELECT * FROM utilisateurs WHERE id = ?", (id,))

    def trouver_par_identifiant_ou_email(self, saisie: str):
        return self._un(
            "SELECT * FROM utilisateurs WHERE identifiant = ? OR email = ?", (saisie, saisie)
        )

    def _un(self, requete, parametres):
        ligne = self.connexion.execute(requete, parametres).fetchone()
        if ligne is None:
            return None
        # hash déjà calculé : pas de mot de passe en clair
        return Utilisateur(ligne["identifiant"], ligne["email"], None, ligne["id"], ligne["mot_de_passe_hash"])
