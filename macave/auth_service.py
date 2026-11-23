import re
import sqlite3

from macave.cave_repository import CaveRepository
from macave.erreurs import AuthentificationError, DonneesInvalidesError
from macave.utilisateur import Utilisateur, hacher_mot_de_passe
from macave.utilisateur_repository import UtilisateurRepository

IDENTIFIANT_VALIDE = re.compile(r"[A-Za-z0-9_.-]{3,30}")
EMAIL_VALIDE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
LONGUEUR_MIN_MOT_DE_PASSE = 8


class AuthService:
    # Inscription, profil et connexion

    def __init__(self, connexion):
        self.connexion = connexion
        self.utilisateurs = UtilisateurRepository(connexion)

    def inscrire(self, identifiant: str, email: str, mot_de_passe: str, confirmation: str) -> Utilisateur:
        identifiant = identifiant.strip()
        email = email.strip().lower()

        erreurs = {}
        if not IDENTIFIANT_VALIDE.fullmatch(identifiant):
            erreurs["identifiant"] = "L'identifiant doit faire 3 à 30 caractères (lettres, chiffres, _ . -)."
        if len(email) > 254 or not EMAIL_VALIDE.fullmatch(email):
            erreurs["email"] = "Adresse e-mail invalide."
        if len(mot_de_passe) < LONGUEUR_MIN_MOT_DE_PASSE:
            erreurs["mot_de_passe"] = f"Le mot de passe doit faire au moins {LONGUEUR_MIN_MOT_DE_PASSE} caractères."
        elif mot_de_passe != confirmation:
            erreurs["confirmation"] = "Les deux mots de passe ne correspondent pas."
        if erreurs:
            raise DonneesInvalidesError(erreurs)

        utilisateur = Utilisateur(identifiant, email, mot_de_passe)
        try:
            with self.connexion:  # commit si tout va bien, rollback sinon
                self.utilisateurs.inserer(utilisateur)
                # une cave par compte
                CaveRepository(self.connexion).creer(utilisateur.id)
        except sqlite3.IntegrityError as e:
            # doublon refusé par la contrainte UNIQUE
            if "identifiant" in str(e):
                raise DonneesInvalidesError({"identifiant": "Cet identifiant est déjà utilisé."})
            if "email" in str(e):
                raise DonneesInvalidesError({"email": "Cette adresse e-mail est déjà utilisée."})
            raise
        return utilisateur

    def modifier_profil(self, utilisateur: Utilisateur, email: str, mot_de_passe_actuel: str,
                        nouveau_mot_de_passe: str, confirmation: str) -> None:
        # Le mot de passe actuel est demandé pour en changer
        email = email.strip().lower()
        changer_mot_de_passe = nouveau_mot_de_passe != ""

        erreurs = {}
        if len(email) > 254 or not EMAIL_VALIDE.fullmatch(email):
            erreurs["email"] = "Adresse e-mail invalide."
        if changer_mot_de_passe:
            if not utilisateur.verifier_mot_de_passe(mot_de_passe_actuel):
                erreurs["mot_de_passe_actuel"] = "Le mot de passe actuel est incorrect."
            if len(nouveau_mot_de_passe) < LONGUEUR_MIN_MOT_DE_PASSE:
                erreurs["nouveau_mot_de_passe"] = (
                    f"Le mot de passe doit faire au moins {LONGUEUR_MIN_MOT_DE_PASSE} caractères.")
            elif nouveau_mot_de_passe != confirmation:
                erreurs["confirmation"] = "Les deux mots de passe ne correspondent pas."
        if erreurs:
            raise DonneesInvalidesError(erreurs)

        # on ne modifie l'objet qu'une fois tout vérifié
        if changer_mot_de_passe:
            utilisateur.modifier_profil(email, nouveau_mot_de_passe)
        else:
            utilisateur.modifier_profil(email)
        try:
            with self.connexion:
                self.utilisateurs.modifier(utilisateur)
        except sqlite3.IntegrityError:
            # e-mail déjà pris par un autre compte
            raise DonneesInvalidesError({"email": "Cette adresse e-mail est déjà utilisée."})

    def authentifier(self, identifiant_ou_email: str, mot_de_passe: str) -> Utilisateur:
        utilisateur = self.utilisateurs.trouver_par_identifiant_ou_email(identifiant_ou_email.strip())
        if utilisateur is None:
            hacher_mot_de_passe(mot_de_passe)  # même temps de calcul qu'un vrai compte
        if utilisateur is None or not utilisateur.verifier_mot_de_passe(mot_de_passe):
            # même message : on ne dit pas si le compte existe
            raise AuthentificationError("Identifiant ou mot de passe incorrect.")
        return utilisateur
