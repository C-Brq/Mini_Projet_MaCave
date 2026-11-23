import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA = Path(__file__).with_name("schema.sql")


def connecter(chemin) -> sqlite3.Connection:
    # Ouvre la base (créée si besoin)
    connexion = sqlite3.connect(chemin)
    connexion.row_factory = sqlite3.Row            # accès aux colonnes par leur nom
    connexion.execute("PRAGMA foreign_keys = ON")  # désactivé par défaut dans SQLite
    return connexion


def initialiser_schema(connexion: sqlite3.Connection) -> None:
    connexion.executescript(SCHEMA.read_text(encoding="utf-8"))


def get_db() -> sqlite3.Connection:
    # Une connexion par requête
    if "db" not in g:
        g.db = connecter(current_app.config["DATABASE"])
    return g.db


def fermer_db(erreur=None) -> None:
    connexion = g.pop("db", None)
    if connexion is not None:
        connexion.close()
