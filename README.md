# MaCave – gestion collaborative d'une cave à vin

Mini-projet ETRS711 : application web Python (Flask + SQLite) exécutée en local. Chaque utilisateur a une
cave privée composée d'étagères, y range des bouteilles, les archive après dégustation avec une note et un
commentaire visibles par la communauté. Le sujet est dans `ETRS711_Mini_Projet_MaCave_version_modifiee.pdf`.

## Fonctionnalités

- **Comptes** : inscription, connexion, déconnexion, modification du profil (e-mail, mot de passe).
- **Cave et étagères** : création, modification, suppression, occupation `x / y` et taux d'occupation.
- **Catalogue de vins** commun à tous, sans doublon ; **bouteilles** : ajout de plusieurs exemplaires
  identiques, déplacement, modification du prix et de la date, retrait définitif, archivage.
- **Évaluations** : note de 0 à 20 et commentaire à l'archivage, visibles par tous les utilisateurs
  connectés sur la fiche du vin ; note moyenne communautaire (« Non évalué » sans note) ; modification de
  ses propres évaluations uniquement.
- **Consultation** : stock, catalogue et historique avec recherche (nom ou domaine), filtre par type et tri dans
  les deux sens ; tableau de bord (bouteilles, références, étagères, occupation globale, valeur du stock).

## Installation

Python 3.9 ou plus récent est nécessaire (SQLite est fourni avec Python). Dans le dossier du projet :

```
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS
pip install -r requirements.txt
```

`requirements.txt` contient Flask et pytest (pour les tests).

## Initialisation de la base et lancement

```
flask --app macave.app run --debug
```

Puis ouvrir <http://127.0.0.1:5000>. Il n'y a rien à initialiser à la main : au premier lancement, l'application
crée tout dans le dossier `instance/` (ignoré par git) :

- `instance/macave.db` : la base SQLite. Son schéma est dans `macave/schema.sql` ; il est rejoué à chaque
  démarrage sans danger (`CREATE TABLE IF NOT EXISTS`), les données existantes ne sont pas touchées ;
- `instance/secret_key` : la clé qui signe les sessions. On peut la fournir autrement avec la variable
  d'environnement `MACAVE_SECRET_KEY`.

Pour repartir de zéro, arrêter le serveur et supprimer le dossier `instance/`.

## Jeu de démonstration

Sur une base vide (donc après avoir supprimé `instance/` si besoin) :

```
python -m macave.demo
```

Il crée deux utilisateurs, plusieurs étagères et vins, cinq exemplaires identiques d'un même vin, des bouteilles
archivées et des évaluations (le même vin reçoit 16, 12 et 17 : moyenne 15 / 20). Comptes de démonstration
(publics, ils ne servent qu'à la démo) : `alice` / `motdepasse1` et `bob` / `motdepasse2`. La commande refuse de
s'exécuter si la base contient déjà des comptes.

## Lancer les tests

```
python -m pytest
```

Chaque test utilise sa propre base SQLite temporaire : aucun risque pour vos données. Les tests couvrent :
les règles métier (`tests/test_modele.py`, sans Flask ni base), la base de données et la persistance après
redémarrage (`tests/test_cave_service.py`, `tests/test_app.py`), le catalogue et les notes communautaires
sans passer par les pages (`tests/test_catalogue_service.py`), les comptes (`tests/test_auth.py`), les pages et
les saisies invalides (`tests/test_routes_*.py`), le contrôle d'accès (`tests/test_acces.py` : toutes les
pages privées exigent d'être connecté, test qui parcourt automatiquement toutes les adresses de l'application),
la recherche et le tri (`tests/test_recherche.py`), l'affichage sans internet (`tests/test_affichage.py` : CSS et
image de fond servis localement, aucune adresse externe dans les pages), la protection CSRF (`tests/test_csrf.py` :
seul test où la vérification du jeton est active, les autres envoient leurs formulaires sans jeton) et le jeu de
démonstration (`tests/test_demo.py`).

### Scénarios du sujet et tests correspondants

| Scénario | Test |
|---|---|
| Créer un compte | `test_inscription_enregistre_le_compte_dans_sqlite`, `test_l_inscription_cree_la_cave_privee` |
| Étagère de capacité 10 : occupation 0/10 | `test_creer_une_etagere_de_capacite_10_affiche_0_sur_10` |
| 5 bouteilles identiques : 5 exemplaires, une référence | `test_ajouter_5_bouteilles_identiques_donne_5_exemplaires_et_une_seule_reference` |
| 6 bouteilles sur une étagère à 5/10 : refus, rien d'ajouté | `test_ajouter_6_bouteilles_a_une_etagere_a_5_sur_10_est_refuse_sans_ajout_partiel` |
| Déplacer une bouteille | `test_deplacer_une_bouteille_met_a_jour_l_occupation_des_deux_etageres` |
| Archiver un exemplaire parmi 5 | `test_archiver_un_exemplaire_parmi_5_laisse_4_en_stock_et_1_dans_l_historique` |
| Notes 16, 12 et 17 : moyenne 15/20 | `test_les_notes_16_12_17_donnent_une_moyenne_communautaire_de_15_sur_20` |
| Second compte : stock du premier inaccessible | `test_acces_direct_aux_bouteilles_d_un_autre_compte_refuse` |
| Référence partagée : évaluations visibles des deux comptes | `test_une_reference_partagee_montre_les_evaluations_aux_deux_comptes` |
| Supprimer une étagère non vide : refus et message | `test_supprimer_une_etagere_non_vide_est_refuse_avec_un_message` |

## Organisation du dépôt

```
macave/
  app.py                     création de l'application Flask et page d'accueil / tableau de bord
  routes_auth.py             inscription, connexion, déconnexion
  routes_cave.py             pages réservées : profil, étagères, bouteilles, historique
  routes_vins.py             catalogue des vins, ajout de bouteilles
  auth_service.py            comptes : validation côté serveur, création, profil
  cave_service.py            opérations sur la cave, une transaction chacune
  catalogue_service.py       catalogue et évaluations communes
  recherche.py               recherche, filtre et tri des listes
  formulaires.py             conversion du texte des formulaires (nombres, dates)
  affichage.py               textes affichés dans les pages (note « 15 / 20 », prix, dates...)
  csrf.py                    jeton CSRF : création et vérification à chaque envoi de formulaire
  *_repository.py            requêtes SQL (utilisateurs, cave, vins)
  db.py, schema.sql          connexion SQLite et schéma
  utilisateur.py, cave_privee.py, etagere.py, bouteille.py, vin.py, evaluation.py, enums.py
                             classes métier, validation.py : contrôles de saisie
  demo.py                    jeu de démonstration
  templates/                 une page HTML complète par fichier, toutes sur le même modèle
                             (seuls {{ }}, if et for sont utilisés)
  static/style.css           toute la mise en page, en CSS simple (thème noir et rouge façon Netflix)
  static/fond.svg            l'image de fond (un dessin de bouteilles) ; à remplacer par une photo si on veut
tests/                       tests pytest
docs/uml/                    diagrammes UML (classes en draw.io ; cas d'utilisation, séquences,
                             modèle relationnel et architecture en Mermaid)
```

## Choix de conception

- **Quatre couches** : pages HTML (templates) ; web (routes Flask : sessions, accès, lecture des formulaires) ;
  métier (classes Python qui appliquent les règles) ; persistance (SQL avec le module `sqlite3`, sans ORM).
  Les règles (capacité, déplacement, archivage, dates, identité d'un vin) sont dans les classes du métier,
  testées sans HTTP ni base. La note moyenne fait exception : elle porte sur les évaluations de tous les
  utilisateurs, alors qu'une cave ne charge que les siennes ; elle est calculée à un seul endroit,
  `CatalogueService.note_moyenne` (`AVG` en SQL), testé lui aussi sans HTTP (`tests/test_catalogue_service.py`).
  Voir `docs/uml/README.md` pour le schéma.
- **Une opération = une transaction.** Chaque opération de `CaveService` charge la cave de l'utilisateur,
  applique la règle sur les objets Python, puis écrit dans la base. Si la règle refuse, rien n'est écrit (tout
  ou rien, même pour la création d'un vin faite dans la même opération). `BEGIN IMMEDIATE` verrouille la base en
  écriture pour qu'aucune autre requête ne modifie la cave entre la lecture et l'écriture. Les contraintes SQL
  (`CHECK`, `UNIQUE`, clés étrangères) servent de dernier rempart.
- **Contrôle d'accès côté serveur (R1).** Toutes les pages de `routes_cave.py` et `routes_vins.py` exigent
  d'être connecté (`exiger_connexion`, exécuté avant chaque page, y compris en accès direct à l'URL).
  Une étagère, une bouteille ou une évaluation n'est cherchée que dans la cave de l'utilisateur connecté ; sinon
  la réponse est 404, sans distinguer « n'existe pas » de « appartient à quelqu'un d'autre ».
- **Identité d'une référence de vin.** Un vin est identifié par (domaine, nom, type, millésime, région),
  comparés sans tenir compte de la casse ni des espaces en trop (`Vin.cle_identite()` : texte en minuscules).
  Les espaces sont nettoyés à la création, et la colonne `vins.cle_identite` est `UNIQUE` : impossible d'avoir
  deux fois la même référence. Les accents comptent : « Rosé » et « Rose » sont deux vins différents. Le prix, la
  description, la photo et les commentaires ne font pas partie de l'identité.
- **Note moyenne.** Somme des notes divisée par leur nombre, calculée à chaque affichage (`AVG` en SQL) : toute
  modification d'une note est donc tout de suite répercutée. Chaque dégustation compte pour une note, même si
  c'est le même utilisateur (R10). Sans évaluation, la moyenne vaut « Non évalué » (et non 0). La publication
  d'une évaluation n'affiche que l'auteur, la note, le commentaire et la date, jamais le contenu de sa cave.
  Le calcul n'existe qu'à cet endroit (pas de seconde version en Python dans la classe `Vin`).
- **Recherche et tri** (`recherche.py`) : filtrage et tri faits en Python sur les listes en mémoire, sans
  aucune requête SQL construite avec la saisie de l'utilisateur. La recherche ignore la casse et les accents
  (« chateau » trouve « Château »). Les critères de tri sont limités à une liste fixe.
- **Valeurs absentes** : un vin sans note (ou une bouteille sans valeur pour le critère) est toujours placé
  **en dernier**, que le tri soit croissant ou décroissant. Sans critère de tri, l'ordre d'origine est conservé.
- **Tri par prix** : l'affichage n'est pas regroupé par référence ; chaque ligne est un exemplaire, et le tri par
  prix porte donc sur le prix payé pour chaque exemplaire (la quantité de chaque vin se voit sur sa fiche).
- **Mots de passe** : salés et hachés (PBKDF2-SHA256), jamais stockés en clair. Les messages de connexion sont les
  mêmes que le compte existe ou non.
- **Prix** : nombres à virgule (`float`), arrondis au centime pour la valeur du stock. Saisie avec point ou virgule.
- **Dates** : `date_ajout` et `date_sortie` (AAAA-MM-JJ), saisies avec un champ de date du navigateur
  (`<input type="date">`). Aucune des deux ne peut être dans le futur, et une bouteille ne peut pas être archivée
  avant sa date d'ajout (le même jour est accepté). La date d'une évaluation est celle de son enregistrement.
- **Limites des saisies** (`validation.py`) : les entiers (capacité, quantité, millésime) vont de 1 à 1 000 000,
  car SQLite ne sait pas ranger un entier supérieur à 2⁶³ ; les noms (domaine, vin, région, étagère) font 100
  caractères au plus, la description et le commentaire 1 000, l'adresse de la photo 500. Le caractère `|` est
  interdit dans le domaine, le nom et la région : c'est le séparateur de la clé d'identité d'un vin, et sans
  cette interdiction « A\|B » + « C » et « A » + « B\|C » seraient pris pour le même vin.
- **Confirmation** : « Retirer la bouteille » et « Supprimer l'étagère » ouvrent une boîte de confirmation du
  navigateur avant l'envoi (`confirm()` en JavaScript, écrit directement dans le formulaire).
- **Protection CSRF** (`csrf.py`) : chaque session reçoit un jeton aléatoire, placé dans un champ caché de
  **chaque** formulaire POST (y compris connexion et déconnexion). Avant toute requête autre qu'une simple
  consultation, le serveur compare le jeton reçu à celui de la session et répond par une erreur 400 s'ils
  diffèrent. Un site pirate ne peut pas connaître le jeton : il ne peut pas envoyer de formulaire à la place de
  l'utilisateur. Le cookie de session en `SameSite=Lax` reste en complément. Pour ajouter un formulaire POST,
  il faut y mettre `<input type="hidden" name="csrf" value="{{ jeton_csrf() }}">` (un test vérifie que
  tous les formulaires des templates le contiennent).
- **Affichage sans internet** : la mise en page est un seul fichier CSS écrit à la main (`static/style.css`, thème
  noir et rouge façon Netflix), sans framework, sans police ni image chargées depuis le web. L'image de fond est un
  dessin local (`static/fond.svg`). Pour mettre votre propre photo : la copier dans `static/` et changer le nom du
  fichier dans la ligne `background-image` de `style.css`.

## Limites et fonctionnalités non réalisées

- Le hachage utilise 100 000 itérations de PBKDF2, ce qui est inférieur aux recommandations actuelles ; pas de
  réinitialisation de mot de passe ni de vérification de l'adresse e-mail.
- La photo de l'étiquette est une adresse web (`http://` ou `https://`) : pas de téléversement de fichier. C'est
  la seule chose qui peut être chargée depuis internet ; sans connexion, cette image ne s'affiche pas.
- Pas de suppression de compte, de vin ou d'évaluation ; pas de pagination des listes.
- Serveur de développement Flask uniquement (aucun déploiement n'est demandé). SQLite n'accepte qu'une écriture
  à la fois : adapté à un usage local.
