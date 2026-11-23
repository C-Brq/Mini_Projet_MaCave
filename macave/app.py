import os
import secrets
from pathlib import Path

from flask import Flask, g, render_template

from macave import affichage, csrf, db, routes_auth, routes_cave, routes_vins
from macave.cave_service import CaveService


def create_app(config: dict = None) -> Flask:
    app = Flask(__name__)
    app.config["DATABASE"] = os.path.join(app.instance_path, "macave.db")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # cookie non envoyé depuis un autre site
    app.config["CSRF_ACTIVE"] = True               # vérification du jeton CSRF
    app.config.update(config or {})

    if not app.config.get("SECRET_KEY"):  # Flask la définit à None par défaut
        app.config["SECRET_KEY"] = _cle_secrete(app)

    # crée le dossier de la base
    os.makedirs(os.path.dirname(os.path.abspath(app.config["DATABASE"])), exist_ok=True)
    connexion = db.connecter(app.config["DATABASE"])
    db.initialiser_schema(connexion)
    connexion.close()

    app.teardown_appcontext(db.fermer_db)
    app.register_blueprint(routes_auth.bp)
    app.register_blueprint(routes_cave.bp)
    app.register_blueprint(routes_vins.bp)

    # Après les blueprints : l'utilisateur est chargé avant
    app.before_request(csrf.verifier_csrf)

    @app.errorhandler(400)
    def formulaire_refuse(erreur):
        return render_template("400.html"), 400

    @app.errorhandler(404)
    def page_introuvable(erreur):
        return render_template("404.html"), 404

    # Fonctions utilisables dans les templates
    app.jinja_env.globals["jeton_csrf"] = csrf.jeton_csrf
    app.jinja_env.globals["texte_note"] = affichage.texte_note
    app.jinja_env.globals["texte_prix"] = affichage.texte_prix
    app.jinja_env.globals["texte_date"] = affichage.texte_date
    app.jinja_env.globals["pourcentage_entier"] = affichage.pourcentage_entier

    @app.route("/")
    def accueil():
        # Visiteur : page de présentation
        if g.utilisateur is None:
            return render_template("accueil.html")

        # Connecté : tableau de bord
        cave = CaveService(db.get_db()).charger_cave(g.utilisateur)
        occupation = cave.occupation_globale()  # None si aucune étagère
        if occupation is None:
            texte_occupation = None
        else:
            texte_occupation = affichage.texte_pourcentage(occupation)
        return render_template(
            "tableau_de_bord.html",
            nb_bouteilles=cave.nb_bouteilles(),
            nb_references=cave.nb_references(),
            nb_etageres=len(cave.etageres),
            texte_occupation=texte_occupation,
            capacite_totale=cave.capacite_totale(),
            valeur_stock=affichage.texte_prix(cave.valeur_stock()),
            nb_degustations=len(cave.historique()),
        )

    return app


def _cle_secrete(app: Flask) -> str:
    # Clé des sessions : variable d'environnement ou fichier local
    if os.environ.get("MACAVE_SECRET_KEY"):
        return os.environ["MACAVE_SECRET_KEY"]
    fichier = Path(app.instance_path) / "secret_key"
    if not fichier.exists():
        os.makedirs(app.instance_path, exist_ok=True)
        fichier.write_text(secrets.token_hex(32))
        os.chmod(fichier, 0o600)
    return fichier.read_text().strip()
