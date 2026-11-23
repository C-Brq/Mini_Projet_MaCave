# Jeu de démonstration, sur une base vide : python -m macave.demo
from datetime import date

from macave import db
from macave.app import create_app
from macave.auth_service import AuthService
from macave.catalogue_service import CatalogueService
from macave.cave_service import CaveService
from macave.enums import TypeVin
from macave.vin import Vin


def creer_donnees_demo(connexion) -> None:
    # Refuse si la base contient déjà des comptes
    nb_utilisateurs = connexion.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0]
    if nb_utilisateurs > 0:
        raise ValueError("La base contient déjà des utilisateurs : le jeu de démonstration n'a pas été créé.")

    auth = AuthService(connexion)
    caves = CaveService(connexion)
    catalogue = CatalogueService(connexion)

    # Les utilisateurs
    alice = auth.inscrire("alice", "alice@example.fr", "motdepasse1", "motdepasse1")
    bob = auth.inscrire("bob", "bob@example.fr", "motdepasse2", "motdepasse2")

    # Le catalogue, partagé entre alice et bob
    montelena, _ = catalogue.creer_vin(Vin(
        "Château Montelena", "Cabernet Sauvignon", TypeVin.ROUGE, 1967, "Californie",
        "Un grand rouge californien, célèbre pour avoir battu des bordeaux lors d'une dégustation à l'aveugle."))
    chardonnay, _ = catalogue.creer_vin(Vin(
        "Domaine des Chênes", "Chardonnay", TypeVin.BLANC, 2018, "Bourgogne",
        "Un blanc rond et beurré, avec une pointe de noisette."))
    bordeaux, _ = catalogue.creer_vin(Vin(
        "Château Lavigne", "Bordeaux supérieur", TypeVin.ROUGE, 2015, "Bordeaux"))
    rose, _ = catalogue.creer_vin(Vin(
        "Domaine Solane", "Côtes de Provence", TypeVin.ROSE, 2022, "Provence",
        "Un rosé frais, à boire en terrasse."))
    cremant, _ = catalogue.creer_vin(Vin(
        "Maison Perrin", "Crémant d'Alsace", TypeVin.EFFERVESCENT, 2020, "Alsace"))
    riesling, _ = catalogue.creer_vin(Vin(
        "Domaine du Val", "Riesling", TypeVin.BLANC, 2019, "Alsace"))

    # Cave d'alice
    principale = caves.creer_etagere(alice, "Cave principale", 12)
    cellier = caves.creer_etagere(alice, "Cellier", 6)
    vitrine = caves.creer_etagere(alice, "Vitrine", 4)

    # achat avant les dates de dégustation
    achat = date(2025, 6, 1)

    # 5 exemplaires d'une seule référence
    caves.ajouter_bouteilles(alice, montelena, principale.id, 5, 85, achat)
    caves.ajouter_bouteilles(alice, chardonnay, principale.id, 3, 24, achat)
    caves.ajouter_bouteilles(alice, bordeaux, cellier.id, 2, 18.5, achat)
    caves.ajouter_bouteilles(alice, rose, vitrine.id, 1, 9.9, achat)

    # Cave de bob
    salon = caves.creer_etagere(bob, "Étagère du salon", 8)
    cave_a_vin = caves.creer_etagere(bob, "Cave à vin", 20)

    caves.ajouter_bouteilles(bob, cremant, salon.id, 4, 12, achat)
    caves.ajouter_bouteilles(bob, riesling, cave_a_vin.id, 2, 15, achat)
    caves.ajouter_bouteilles(bob, montelena, cave_a_vin.id, 2, 90, achat)  # la même référence qu'alice

    # Dégustations
    # Montelena : 16, 12 et 17, moyenne 15 / 20
    cave_alice = caves.charger_cave(alice)
    cave_bob = caves.charger_cave(bob)

    montelena_alice = []
    chardonnay_alice = []
    for bouteille in cave_alice.bouteilles_en_stock():
        if bouteille.vin.id == montelena.id:
            montelena_alice.append(bouteille)
        if bouteille.vin.id == chardonnay.id:
            chardonnay_alice.append(bouteille)
    montelena_bob = []
    cremant_bob = []
    for bouteille in cave_bob.bouteilles_en_stock():
        if bouteille.vin.id == montelena.id:
            montelena_bob.append(bouteille)
        if bouteille.vin.id == cremant.id:
            cremant_bob.append(bouteille)

    caves.archiver_bouteille(alice, montelena_alice[0].id, 16, "Puissant, tanins soyeux.", date(2025, 11, 2))
    caves.archiver_bouteille(alice, montelena_alice[1].id, 12, "Un peu fatigué cette fois-ci.", date(2026, 1, 18))
    caves.archiver_bouteille(alice, chardonnay_alice[0].id, 14, "Très agréable avec du poisson.", date(2026, 3, 7))
    caves.archiver_bouteille(bob, montelena_bob[0].id, 17, "Une très belle surprise.", date(2026, 2, 14))
    caves.archiver_bouteille(bob, cremant_bob[0].id, 15, None, date(2025, 12, 31))


def main() -> None:
    # Remplit la base de l'application (dossier instance/)
    app = create_app()  # crée la base si besoin
    connexion = db.connecter(app.config["DATABASE"])
    try:
        creer_donnees_demo(connexion)
    except ValueError as erreur:
        print(erreur)
        print("Pour repartir de zéro : arrêter le serveur, supprimer le dossier instance/, puis relancer.")
        raise SystemExit(1)
    finally:
        connexion.close()
    print("Jeu de démonstration créé.")
    print("Comptes : alice / motdepasse1   et   bob / motdepasse2")


if __name__ == "__main__":
    main()
