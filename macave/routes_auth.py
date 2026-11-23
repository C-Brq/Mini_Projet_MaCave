from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from macave.auth_service import AuthService
from macave.db import get_db
from macave.erreurs import AuthentificationError, DonneesInvalidesError
from macave.utilisateur_repository import UtilisateurRepository

bp = Blueprint("auth", __name__)


@bp.before_app_request
def charger_utilisateur():
    # g.utilisateur : utilisateur connecté ou None
    g.utilisateur = None
    utilisateur_id = session.get("utilisateur_id")
    if utilisateur_id is not None:
        g.utilisateur = UtilisateurRepository(get_db()).trouver(utilisateur_id)
        if g.utilisateur is None:  # compte supprimé : on vide la session
            session.clear()


@bp.route("/inscription", methods=("GET", "POST"))
def inscription():
    valeurs, erreurs = {"identifiant": "", "email": ""}, {}
    if request.method == "POST":
        valeurs = {"identifiant": request.form.get("identifiant", ""), "email": request.form.get("email", "")}
        try:
            AuthService(get_db()).inscrire(
                identifiant=valeurs["identifiant"],
                email=valeurs["email"],
                mot_de_passe=request.form.get("mot_de_passe", ""),
                confirmation=request.form.get("confirmation", ""),
            )
        except DonneesInvalidesError as e:
            erreurs = e.erreurs
        else:
            flash("Votre compte a été créé. Vous pouvez maintenant vous connecter.", "succes")
            return redirect(url_for("auth.connexion"))
    if erreurs:
        code = 400  # saisie refusée
    else:
        code = 200
    return render_template("inscription.html", valeurs=valeurs, erreurs=erreurs), code


@bp.route("/connexion", methods=("GET", "POST"))
def connexion():
    saisie, erreur = "", None
    if request.method == "POST":
        saisie = request.form.get("identifiant", "")
        try:
            utilisateur = AuthService(get_db()).authentifier(saisie, request.form.get("mot_de_passe", ""))
        except AuthentificationError as e:
            erreur = str(e)
        else:
            session.clear()  # nouvelle session à chaque connexion
            session["utilisateur_id"] = utilisateur.id
            return redirect(url_for("accueil"))
    if erreur:
        code = 401  # identifiant ou mot de passe incorrect
    else:
        code = 200
    return render_template("connexion.html", saisie=saisie, erreur=erreur), code


@bp.route("/deconnexion", methods=("POST",))
def deconnexion():
    session.clear()
    return redirect(url_for("accueil"))
