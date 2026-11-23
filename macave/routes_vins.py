# Catalogue partagé et ajout de bouteilles
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from macave.catalogue_service import CatalogueService
from macave.cave_service import CaveService
from macave.db import get_db
from macave.enums import TypeVin
from macave.erreurs import IntrouvableError
from macave.formulaires import TYPES_DE_VIN, lire_entier, lire_nombre
from macave.recherche import SENS, TRIS_CATALOGUE, rechercher
from macave.routes_cave import element_introuvable, exiger_connexion, lire_recherche, options_etageres
from macave.vin import Vin

bp = Blueprint("vins", __name__)

# connexion obligatoire, comme dans routes_cave.py
bp.before_request(exiger_connexion)
bp.register_error_handler(IntrouvableError, element_introuvable)

@bp.route("/vins")
def liste_vins():
    lignes = CatalogueService(get_db()).lister_vins()
    q, type_vin, tri, sens = lire_recherche()
    lignes = rechercher(lignes, q, type_vin, tri, sens)
    return render_template("vins.html", lignes=lignes, q=q, type_vin=type_vin, tri=tri, sens=sens,
                           types=TYPES_DE_VIN, tris=TRIS_CATALOGUE, sens_possibles=SENS)


@bp.route("/vins/nouveau", methods=("GET", "POST"))
def nouveau_vin():
    valeurs = {"domaine": "", "nom": "", "type": "rouge", "millesime": "", "region": "",
               "description": "", "photo_etiquette": ""}
    if request.method == "POST":
        for champ in valeurs:
            valeurs[champ] = request.form.get(champ, "")
        try:
            vin = lire_vin(valeurs)
            vin, cree = CatalogueService(get_db()).creer_vin(vin)
        except ValueError as e:
            flash(str(e), "erreur")
        else:
            if cree:
                flash("Le vin a été ajouté au catalogue.", "succes")
            else:
                flash("Ce vin existe déjà dans le catalogue : voici sa fiche.", "succes")
            return redirect(url_for("vins.fiche_vin", vin_id=vin.id))
    return render_template("vin_nouveau.html", valeurs=valeurs, types=TYPES_DE_VIN)


def lire_vin(valeurs) -> Vin:
    # Construit un Vin depuis le formulaire
    millesime = lire_entier(valeurs["millesime"], "Le millésime")
    types_valides = []
    for valeur, texte in TYPES_DE_VIN:
        types_valides.append(valeur)
    if valeurs["type"] not in types_valides:
        raise ValueError("Le type du vin doit être rouge, blanc, rosé ou effervescent.")
    photo = valeurs["photo_etiquette"].strip()
    if photo != "" and not (photo.startswith("http://") or photo.startswith("https://")):
        raise ValueError("La photo de l'étiquette doit être une adresse web (http:// ou https://).")
    return Vin(valeurs["domaine"], valeurs["nom"], TypeVin(valeurs["type"]), millesime,
               valeurs["region"], valeurs["description"].strip(), photo)


@bp.route("/vins/<int:vin_id>")
def fiche_vin(vin_id):
    catalogue = CatalogueService(get_db())
    vin = catalogue.charger_vin(vin_id)
    moyenne, nb_evaluations = catalogue.note_moyenne(vin_id)
    evaluations = catalogue.evaluations_du_vin(vin_id)

    # seulement mes bouteilles : le stock des autres est privé
    cave = CaveService(get_db()).charger_cave(g.utilisateur)
    mes_bouteilles = []
    for bouteille in cave.bouteilles:
        if bouteille.vin.id == vin_id:
            mes_bouteilles.append(bouteille)

    return render_template("vin.html", vin=vin, moyenne=moyenne, nb_evaluations=nb_evaluations,
                           evaluations=evaluations, mes_bouteilles=mes_bouteilles,
                           etageres=options_etageres(cave.etageres))


@bp.route("/vins/<int:vin_id>/ajouter", methods=("POST",))
def ajouter_bouteilles(vin_id):
    vin = CatalogueService(get_db()).charger_vin(vin_id)
    try:
        etagere_id = lire_entier(request.form.get("etagere", ""), "L'étagère")
        quantite = lire_entier(request.form.get("quantite", ""), "La quantité")
        prix = lire_nombre(request.form.get("prix", ""), "Le prix d'achat")
        CaveService(get_db()).ajouter_bouteilles(g.utilisateur, vin, etagere_id, quantite, prix)
    except ValueError as e:  # capacité dépassée, quantité ou prix invalide...
        flash(str(e), "erreur")
    else:
        if quantite == 1:
            flash("La bouteille a été ajoutée à votre cave.", "succes")
        else:
            flash(str(quantite) + " bouteilles ont été ajoutées à votre cave.", "succes")
    return redirect(url_for("vins.fiche_vin", vin_id=vin_id))
