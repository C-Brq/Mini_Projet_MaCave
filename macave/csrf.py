# Protection CSRF : un jeton secret par session, vérifié à chaque POST
import secrets

from flask import abort, current_app, request, session


def jeton_csrf() -> str:
    # Jeton de la session, créé au premier appel
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def verifier_csrf() -> None:
    # Avant chaque requête : POST sans le bon jeton = erreur 400
    if not current_app.config["CSRF_ACTIVE"]:
        return  # désactivée dans les tests des pages
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    jeton_recu = request.form.get("csrf", "")
    jeton_attendu = session.get("csrf", "")
    # comparaison à temps constant, en octets pour l'Unicode
    if jeton_attendu == "" or not secrets.compare_digest(jeton_recu.encode(), jeton_attendu.encode()):
        abort(400)
