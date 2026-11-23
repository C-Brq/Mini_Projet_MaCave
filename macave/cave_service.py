from macave.cave_repository import CaveRepository
from macave.erreurs import IntrouvableError
from macave.vin_repository import VinRepository


class CaveService:
    # Une transaction par opération, toujours sur la cave de l'utilisateur

    def __init__(self, connexion):
        self.connexion = connexion
        self.caves = CaveRepository(connexion)
        self.vins = VinRepository(connexion)

    # Outils internes

    def _cave_de(self, utilisateur):
        # Crée la cave si elle manque (anciens comptes)
        cave = self.caves.charger(utilisateur)
        if cave is None:
            self.caves.creer(utilisateur.id)
            cave = self.caves.charger(utilisateur)
        return cave

    def _debut_operation(self, utilisateur):
        # BEGIN IMMEDIATE : verrou d'écriture avant de lire la cave
        self.connexion.execute("BEGIN IMMEDIATE")
        return self._cave_de(utilisateur)

    def _chercher(self, elements, id, nom_element):
        # Cherche par id, sinon IntrouvableError
        for element in elements:
            if element.id == id:
                return element
        raise IntrouvableError(nom_element + " introuvable.")

    # Lecture

    def charger_cave(self, utilisateur):
        with self.connexion:
            return self._cave_de(utilisateur)

    def charger_etagere(self, utilisateur, etagere_id):
        # Cherchée uniquement dans sa cave (R1)
        cave = self.charger_cave(utilisateur)
        return self._chercher(cave.etageres, etagere_id, "Étagère")

    def charger_bouteille(self, utilisateur, bouteille_id):
        cave = self.charger_cave(utilisateur)
        return self._chercher(cave.bouteilles, bouteille_id, "Bouteille")

    # Étagères

    def creer_etagere(self, utilisateur, nom, capacite_max):
        with self.connexion:  # commit à la fin, rollback en cas d'erreur
            cave = self._debut_operation(utilisateur)
            etagere = cave.creer_etagere(nom, capacite_max)  # règles métier (peut lever ValueError)
            self.caves.inserer_etagere(cave, etagere)
        return etagere

    def modifier_etagere(self, utilisateur, etagere_id, nom, capacite_max):
        with self.connexion:
            cave = self._debut_operation(utilisateur)
            etagere = self._chercher(cave.etageres, etagere_id, "Étagère")
            cave.modifier_etagere(etagere, nom, capacite_max)
            self.caves.modifier_etagere(etagere)
        return etagere

    def supprimer_etagere(self, utilisateur, etagere_id):
        with self.connexion:
            cave = self._debut_operation(utilisateur)
            etagere = self._chercher(cave.etageres, etagere_id, "Étagère")
            cave.supprimer_etagere(etagere)  # refuse si l'étagère n'est pas vide (R5)
            self.caves.supprimer_etagere(etagere)

    # Bouteilles

    def ajouter_bouteilles(self, utilisateur, vin, etagere_id, quantite, prix_achat, date_ajout=None):
        # Crée le vin s'il n'existe pas ; tout est annulé en cas de refus
        with self.connexion:
            cave = self._debut_operation(utilisateur)
            etagere = self._chercher(cave.etageres, etagere_id, "Étagère")
            vin, _ = self.vins.trouver_ou_creer(vin)  # on reprend la référence qui existe déjà
            nouvelles = cave.ajouter_bouteilles(vin, etagere, quantite, prix_achat, date_ajout)
            for bouteille in nouvelles:
                self.caves.inserer_bouteille(cave, bouteille)
        return nouvelles

    def deplacer_bouteille(self, utilisateur, bouteille_id, etagere_destination_id):
        with self.connexion:
            cave = self._debut_operation(utilisateur)
            bouteille = self._chercher(cave.bouteilles, bouteille_id, "Bouteille")
            destination = self._chercher(cave.etageres, etagere_destination_id, "Étagère")
            bouteille.deplacer_vers(destination)  # refuse si la destination est pleine (R7)
            self.caves.modifier_bouteille(bouteille)
        return bouteille

    def retirer_bouteille(self, utilisateur, bouteille_id):
        # Retrait définitif, le vin reste au catalogue
        with self.connexion:
            cave = self._debut_operation(utilisateur)
            bouteille = self._chercher(cave.bouteilles, bouteille_id, "Bouteille")
            bouteille.retirer()
            self.caves.supprimer_bouteille(bouteille)

    def archiver_bouteille(self, utilisateur, bouteille_id, note, commentaire=None, date_sortie=None):
        # Sans date de sortie, on prend aujourd'hui
        with self.connexion:
            cave = self._debut_operation(utilisateur)
            bouteille = self._chercher(cave.bouteilles, bouteille_id, "Bouteille")
            evaluation = bouteille.archiver(note, commentaire, date_sortie)  # refuse si déjà archivée (R8)
            self.caves.modifier_bouteille(bouteille)
            self.caves.inserer_evaluation(evaluation)
        return evaluation

    def modifier_bouteille(self, utilisateur, bouteille_id, prix_achat, date_ajout):
        # Prix et date d'ajout uniquement
        with self.connexion:
            cave = self._debut_operation(utilisateur)
            bouteille = self._chercher(cave.bouteilles, bouteille_id, "Bouteille")
            bouteille.modifier_infos(prix_achat, date_ajout)
            self.caves.modifier_bouteille(bouteille)
        return bouteille

    # Évaluations

    def modifier_evaluation(self, utilisateur, evaluation_id, note, commentaire=None):
        # Seules ses propres évaluations sont dans sa cave (R12)
        with self.connexion:
            cave = self._debut_operation(utilisateur)
            evaluations = []
            for bouteille in cave.bouteilles:
                if bouteille.evaluation is not None:
                    evaluations.append(bouteille.evaluation)
            evaluation = self._chercher(evaluations, evaluation_id, "Évaluation")
            evaluation.modifier(utilisateur, note, commentaire)
            self.caves.modifier_evaluation(evaluation)
        return evaluation
