# Pages privées : profil, étagères, bouteilles, historique
from datetime import date

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from macave.auth_service import AuthService
from macave.catalogue_service import CatalogueService
from macave.cave_service import CaveService
from macave.db import get_db
from macave.erreurs import DonneesInvalidesError, IntrouvableError
from macave.formulaires import TYPES_DE_VIN, lire_date, lire_entier, lire_nombre
from macave.recherche import (SENS, TRIS_HISTORIQUE, TRIS_STOCK, lignes_de_bouteilles,
                              rechercher)

bp = Blueprint("cave", __name__)


@bp.before_request
def exiger_connexion():
    # Avant chaque page : connexion obligatoire, même en accès direct
    if g.utilisateur is None:
        flash("Connectez-vous pour accéder à cette page.", "erreur")
        return redirect(url_for("auth.connexion"))


@bp.errorhandler(IntrouvableError)
def element_introuvable(erreur):
    # Absent ou à un autre : 404
    return render_template("404.html"), 404


def lire_recherche():
    # Lit q, type, tri et sens dans l'URL
    q = request.args.get("q", "")
    type_vin = request.args.get("type", "")
    tri = request.args.get("tri", "")
    sens = request.args.get("sens", "asc")
    return q, type_vin, tri, sens


def options_etageres(etageres, a_ignorer=None):
    # Options « nom (occupation) » ; a_ignorer : étagère actuelle
    options = []
    for etagere in etageres:
        if etagere is not a_ignorer:
            texte = etagere.nom + " (" + str(etagere.occupation) + "/" + str(etagere.capacite_max) + ")"
            options.append((etagere.id, texte))
    return options


# Profil

@bp.route("/profil", methods=("GET", "POST"))
def profil():
    email = g.utilisateur.email
    erreurs = {}
    if request.method == "POST":
        email = request.form.get("email", "")
        try:
            AuthService(get_db()).modifier_profil(
                g.utilisateur,
                email,
                request.form.get("mot_de_passe_actuel", ""),
                request.form.get("nouveau_mot_de_passe", ""),
                request.form.get("confirmation", ""),
            )
        except DonneesInvalidesError as e:
            erreurs = e.erreurs
        else:
            flash("Votre profil a été mis à jour.", "succes")
            return redirect(url_for("cave.profil"))
    if erreurs:
        code = 400
    else:
        code = 200
    return render_template("profil.html", email=email, erreurs=erreurs), code


# Étagères
# On tente l'opération, on affiche l'erreur éventuelle, puis on redirige

@bp.route("/etageres", methods=("GET", "POST"))
def liste_etageres():
    service = CaveService(get_db())
    if request.method == "POST":
        try:
            capacite = lire_entier(request.form.get("capacite", ""), "La capacité")
            service.creer_etagere(g.utilisateur, request.form.get("nom", ""), capacite)
        except ValueError as e:
            flash(str(e), "erreur")
        else:
            flash("L'étagère a été créée.", "succes")
        return redirect(url_for("cave.liste_etageres"))

    cave = service.charger_cave(g.utilisateur)
    return render_template("etageres.html", cave=cave)


@bp.route("/etageres/<int:etagere_id>")
def fiche_etagere(etagere_id):
    etagere = CaveService(get_db()).charger_etagere(g.utilisateur, etagere_id)
    return render_template("etagere.html", etagere=etagere)


@bp.route("/etageres/<int:etagere_id>/modifier", methods=("POST",))
def modifier_etagere(etagere_id):
    try:
        capacite = lire_entier(request.form.get("capacite", ""), "La capacité")
        CaveService(get_db()).modifier_etagere(
            g.utilisateur, etagere_id, request.form.get("nom", ""), capacite)
    except ValueError as e:
        flash(str(e), "erreur")
    else:
        flash("L'étagère a été modifiée.", "succes")
    return redirect(url_for("cave.fiche_etagere", etagere_id=etagere_id))


@bp.route("/etageres/<int:etagere_id>/supprimer", methods=("POST",))
def supprimer_etagere(etagere_id):
    try:
        CaveService(get_db()).supprimer_etagere(g.utilisateur, etagere_id)
    except ValueError as e:  # par exemple : l'étagère n'est pas vide
        flash(str(e), "erreur")
        return redirect(url_for("cave.fiche_etagere", etagere_id=etagere_id))
    flash("L'étagère a été supprimée.", "succes")
    return redirect(url_for("cave.liste_etageres"))


# Bouteilles

@bp.route("/bouteilles")
def liste_bouteilles():
    cave = CaveService(get_db()).charger_cave(g.utilisateur)
    moyennes = CatalogueService(get_db()).moyennes_par_vin()
    lignes = lignes_de_bouteilles(cave.bouteilles_en_stock(), moyennes)
    q, type_vin, tri, sens = lire_recherche()
    lignes = rechercher(lignes, q, type_vin, tri, sens)
    return render_template("bouteilles.html", lignes=lignes, q=q, type_vin=type_vin, tri=tri, sens=sens,
                           types=TYPES_DE_VIN, tris=TRIS_STOCK, sens_possibles=SENS,
                           nb_affichees=len(lignes), nb_en_stock=cave.nb_bouteilles())


@bp.route("/bouteilles/<int:bouteille_id>")
def fiche_bouteille(bouteille_id):
    bouteille = CaveService(get_db()).charger_bouteille(g.utilisateur, bouteille_id)
    moyenne, nb_evaluations = CatalogueService(get_db()).note_moyenne(bouteille.vin.id)
    return render_template(
        "bouteille.html", bouteille=bouteille, moyenne=moyenne, nb_evaluations=nb_evaluations,
        etageres_possibles=options_etageres(bouteille.cave.etageres, bouteille.etagere),
        aujourd_hui=date.today().isoformat())


@bp.route("/bouteilles/<int:bouteille_id>/modifier", methods=("POST",))
def modifier_bouteille(bouteille_id):
    try:
        prix = lire_nombre(request.form.get("prix", ""), "Le prix d'achat")
        date_ajout = lire_date(request.form.get("date_ajout", ""), "La date d'ajout")
        CaveService(get_db()).modifier_bouteille(g.utilisateur, bouteille_id, prix, date_ajout)
    except ValueError as e:
        flash(str(e), "erreur")
    else:
        flash("La bouteille a été modifiée.", "succes")
    return redirect(url_for("cave.fiche_bouteille", bouteille_id=bouteille_id))


@bp.route("/bouteilles/<int:bouteille_id>/deplacer", methods=("POST",))
def deplacer_bouteille(bouteille_id):
    try:
        etagere_id = lire_entier(request.form.get("etagere", ""), "L'étagère")
        CaveService(get_db()).deplacer_bouteille(g.utilisateur, bouteille_id, etagere_id)
    except ValueError as e:  # par exemple : la destination est pleine
        flash(str(e), "erreur")
    else:
        flash("La bouteille a été déplacée.", "succes")
    return redirect(url_for("cave.fiche_bouteille", bouteille_id=bouteille_id))


@bp.route("/bouteilles/<int:bouteille_id>/retirer", methods=("POST",))
def retirer_bouteille(bouteille_id):
    try:
        CaveService(get_db()).retirer_bouteille(g.utilisateur, bouteille_id)
    except ValueError as e:
        flash(str(e), "erreur")
        return redirect(url_for("cave.fiche_bouteille", bouteille_id=bouteille_id))
    flash("La bouteille a été retirée de votre cave.", "succes")
    return redirect(url_for("cave.liste_bouteilles"))


@bp.route("/bouteilles/<int:bouteille_id>/archiver", methods=("POST",))
def archiver_bouteille(bouteille_id):
    try:
        note = lire_nombre(request.form.get("note", ""), "La note")
        commentaire = request.form.get("commentaire", "").strip()
        if commentaire == "":
            commentaire = None  # le commentaire est facultatif
        texte_date = request.form.get("date_sortie", "").strip()
        if texte_date == "":
            date_sortie = None  # sans date : aujourd'hui
        else:
            date_sortie = lire_date(texte_date, "La date de sortie")
        CaveService(get_db()).archiver_bouteille(g.utilisateur, bouteille_id, note, commentaire, date_sortie)
    except ValueError as e:  # note hors de 0 à 20, bouteille déjà archivée...
        flash(str(e), "erreur")
    else:
        flash("La bouteille a été archivée avec son évaluation.", "succes")
    return redirect(url_for("cave.fiche_bouteille", bouteille_id=bouteille_id))


@bp.route("/bouteilles/<int:bouteille_id>/evaluation", methods=("POST",))
def modifier_evaluation(bouteille_id):
    # Seule la cave de l'auteur contient l'évaluation (R12)
    service = CaveService(get_db())
    bouteille = service.charger_bouteille(g.utilisateur, bouteille_id)
    if bouteille.evaluation is None:
        raise IntrouvableError("Évaluation introuvable.")
    try:
        note = lire_nombre(request.form.get("note", ""), "La note")
        commentaire = request.form.get("commentaire", "").strip()
        if commentaire == "":
            commentaire = None
        service.modifier_evaluation(g.utilisateur, bouteille.evaluation.id, note, commentaire)
    except ValueError as e:
        flash(str(e), "erreur")
    else:
        flash("Votre évaluation a été modifiée.", "succes")
    return redirect(url_for("cave.fiche_bouteille", bouteille_id=bouteille_id))


# Historique

@bp.route("/historique")
def historique():
    cave = CaveService(get_db()).charger_cave(g.utilisateur)
    moyennes = CatalogueService(get_db()).moyennes_par_vin()
    lignes = lignes_de_bouteilles(cave.historique(), moyennes)
    # pas de filtre ici, seulement le tri
    q, type_vin, tri, sens = lire_recherche()
    lignes = rechercher(lignes, "", "", tri, sens)
    return render_template("historique.html", lignes=lignes, tri=tri, sens=sens,
                           tris=TRIS_HISTORIQUE, sens_possibles=SENS)
