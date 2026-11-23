# Diagrammes UML de MaCave

Les diagrammes sont cohérents avec le code actuel. Les schémas écrits en Mermaid sont du texte : GitHub et
GitLab les affichent directement et ils se modifient à la main. Le diagramme de classes est un fichier
draw.io (source éditable).

| Diagramme | Où |
|---|---|
| Diagramme de classes | [diagramme_de_classes.drawio](diagramme_de_classes.drawio) (à ouvrir avec <https://app.diagrams.net>) |
| Diagramme de cas d'utilisation | ci-dessous |
| Diagrammes de séquence (ajout multiple, déplacement, archivage avec évaluation, envoi d'un formulaire et jeton CSRF) | ci-dessous |
| Modèle relationnel | ci-dessous |
| Architecture en couches | ci-dessous |

## Diagramme de classes (résumé)

Le diagramme complet, avec les attributs typés et les multiplicités, est dans le fichier draw.io.
Voici les relations principales, pour les lire sans ouvrir le fichier :

```mermaid
classDiagram
    direction LR
    class Utilisateur {
        +int id
        +str identifiant
        +str email
        +str mot_de_passe_hash
        +verifier_mot_de_passe(mdp) bool
        +modifier_profil(email, mdp) void
    }
    class CavePrivee {
        +int id
        +appartient_a(utilisateur) bool
        +creer_etagere(nom, capacite_max) Etagere
        +modifier_etagere(etagere, nom, capacite_max) void
        +supprimer_etagere(etagere) void
        +ajouter_bouteilles(vin, etagere, quantite, prix_achat, date_ajout) List~Bouteille~
        +bouteilles_en_stock() List~Bouteille~
        +historique() List~Bouteille~
        +nb_bouteilles() int
        +nb_references() int
        +capacite_totale() int
        +occupation_globale() float
        +valeur_stock() float
    }
    class Etagere {
        +int id
        +str nom
        +int capacite_max
        +int occupation
        +places_libres() int
        +taux_occupation() float
        +est_vide() bool
        +modifier_capacite(capacite_max) void
        +accueillir(bouteilles) void
        +retirer(bouteille) void
    }
    class Vin {
        +int id
        +str domaine
        +str nom
        +TypeVin type
        +int millesime
        +str region
        +str description
        +str photo_etiquette
        +cle_identite() str
        +est_le_meme_vin_que(autre) bool
    }
    class Bouteille {
        +int id
        +float prix_achat
        +date date_ajout
        +StatutBouteille statut
        +date date_sortie
        +est_en_stock() bool
        +modifier_infos(prix_achat, date_ajout) void
        +deplacer_vers(destination) void
        +retirer() void
        +archiver(note, commentaire, date_sortie) Evaluation
    }
    class Evaluation {
        +int id
        +float note
        +str commentaire
        +datetime date
        +est_modifiable_par(utilisateur) bool
        +modifier(auteur, note, commentaire) void
    }
    class TypeVin {
        <<enumeration>>
        ROUGE
        BLANC
        ROSE
        EFFERVESCENT
    }
    class StatutBouteille {
        <<enumeration>>
        EN_STOCK
        ARCHIVEE
    }
    Utilisateur "1" *-- "1" CavePrivee : possède
    CavePrivee "1" *-- "0..*" Etagere : contient
    CavePrivee "1" *-- "0..*" Bouteille : détient
    Etagere "0..1" o-- "0..*" Bouteille : stocke (en stock)
    Vin "1" <-- "0..*" Bouteille : exemplaire de
    Bouteille "1" -- "0..1" Evaluation : donne lieu à
    Evaluation "0..*" --> "1" Vin : concerne
    Utilisateur "1" <-- "0..*" Evaluation : auteur
    Vin --> TypeVin
    Bouteille --> StatutBouteille
    note for Bouteille "Contraintes :\ndate_ajout ≤ date du jour\ndate_ajout ≤ date_sortie ≤ date du jour\nARCHIVEE ⇒ pas d'étagère, date_sortie renseignée\nEN_STOCK ⇒ étagère renseignée, pas de date_sortie"
```

La distinction demandée par le sujet apparaît clairement : un **Vin** est une référence du catalogue
(commune à tous les utilisateurs) ; une **Bouteille** est un exemplaire physique rattaché à une seule cave et à
une seule référence. Cinq bouteilles identiques sont donc cinq `Bouteille` qui pointent vers un seul `Vin`.

La **note moyenne n'est pas une méthode de `Vin`** : elle porte sur les évaluations de *tous* les utilisateurs,
alors qu'un `Vin` chargé avec une cave ne connaît que celles de cet utilisateur. Une `Evaluation` connaît son `Vin`
(navigabilité `Evaluation` → `Vin`), mais un `Vin` n'a pas de liste d'évaluations. La moyenne est calculée à un
seul endroit, `CatalogueService.note_moyenne` (SQL `AVG`), voir le diagramme d'architecture plus bas.

## Diagramme de cas d'utilisation

Mermaid n'a pas de type « cas d'utilisation » : il est dessiné avec un diagramme de flux (acteurs à gauche,
cas d'utilisation dans la frontière du système, `«include»` en pointillés).

```mermaid
flowchart LR
    visiteur(["Visiteur<br/>(non connecté)"])
    utilisateur(["Utilisateur<br/>connecté"])

    subgraph systeme["Système MaCave"]
        direction TB
        creer(["Créer un compte"])
        connexion(["Se connecter / se déconnecter"])
        profil(["Modifier son profil"])
        etageres(["Gérer ses étagères<br/>(créer, modifier, supprimer)"])
        occupation(["Consulter une étagère<br/>(contenu, occupation)"])
        stock(["Consulter ses bouteilles<br/>en stock"])
        modifier_bouteille(["Modifier une bouteille<br/>(prix, date d'ajout)"])
        ajouter(["Ajouter des bouteilles<br/>identiques"])
        reference(["Choisir ou créer<br/>une référence de vin"])
        deplacer(["Déplacer une bouteille"])
        retirer(["Retirer définitivement<br/>une bouteille"])
        archiver(["Archiver une bouteille<br/>après dégustation"])
        evaluer(["Noter et commenter<br/>(0 à 20)"])
        modifier_eval(["Modifier ses évaluations"])
        catalogue(["Consulter le catalogue<br/>et les évaluations d'un vin"])
        rechercher(["Rechercher, filtrer, trier"])
        bord(["Consulter son<br/>tableau de bord"])
        historique(["Consulter son historique<br/>de dégustations"])
        trier_note(["Trier par note<br/>personnelle"])
    end

    visiteur --> creer
    visiteur --> connexion
    utilisateur --> connexion
    utilisateur --> profil
    utilisateur --> etageres
    utilisateur --> occupation
    utilisateur --> stock
    utilisateur --> modifier_bouteille
    utilisateur --> ajouter
    utilisateur --> deplacer
    utilisateur --> retirer
    utilisateur --> archiver
    utilisateur --> modifier_eval
    utilisateur --> catalogue
    utilisateur --> rechercher
    utilisateur --> bord
    utilisateur --> historique
    utilisateur --> trier_note

    ajouter -. "«include»" .-> reference
    archiver -. "«include»" .-> evaluer
    rechercher -. "«extend»" .-> stock
    rechercher -. "«extend»" .-> catalogue
    trier_note -. "«extend»" .-> historique
```

Règle R1 (accès) : tous les cas d'utilisation de l'utilisateur connecté s'appliquent **à sa propre cave** ;
seul le catalogue et les évaluations sont communs à tous les utilisateurs connectés.

## Diagrammes de séquence

### Ajout de plusieurs bouteilles identiques (opération atomique)

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant R as routes_vins
    participant S as CaveService
    participant V as VinRepository
    participant C as CavePrivee
    participant E as Etagere
    participant B as CaveRepository / SQLite

    U->>R: POST /vins/{id}/ajouter (étagère, quantité, prix)
    R->>R: convertit les champs (lire_entier, lire_nombre)
    R->>S: ajouter_bouteilles(utilisateur, vin, étagère, quantité, prix)
    S->>B: BEGIN IMMEDIATE (verrouille la base)
    S->>B: charger(utilisateur) : cave, étagères, bouteilles
    B-->>S: CavePrivee
    S->>V: trouver_ou_creer(vin) (clé d'identité)
    S->>C: ajouter_bouteilles(vin, étagère, quantité, prix)
    C->>C: vérifie quantité > 0, étagère de cette cave et date d'ajout
    C->>E: places_libres()
    alt quantité > places libres
        C-->>S: ValueError « Capacité de l'étagère dépassée »
        S->>B: ROLLBACK (rien n'est enregistré, même pas le vin créé)
        S-->>R: ValueError
        R-->>U: redirige avec le message d'erreur
    else la place suffit
        C->>E: accueillir(nouvelles bouteilles)
        C-->>S: liste des bouteilles créées
        S->>B: INSERT d'une ligne par bouteille
        S->>B: COMMIT
        S-->>R: bouteilles ajoutées
        R-->>U: redirige avec « N bouteilles ont été ajoutées »
    end
```

### Déplacement d'une bouteille

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant R as routes_cave
    participant S as CaveService
    participant Bo as Bouteille
    participant D as Etagere (destination)
    participant B as CaveRepository / SQLite

    U->>R: POST /bouteilles/{id}/deplacer (étagère de destination)
    R->>S: deplacer_bouteille(utilisateur, bouteille, destination)
    S->>B: BEGIN IMMEDIATE puis charger la cave de l'utilisateur
    S->>S: cherche la bouteille et l'étagère DANS cette cave (sinon IntrouvableError)
    S->>Bo: deplacer_vers(destination)
    Bo->>D: accueillir([bouteille])
    alt destination pleine
        D-->>Bo: ValueError « Capacité de l'étagère dépassée »
        S->>B: ROLLBACK
        R-->>U: message d'erreur (404 si la bouteille n'est pas la sienne)
    else
        Bo->>Bo: retire la bouteille de l'ancienne étagère
        S->>B: UPDATE bouteilles SET etagere_id = destination
        S->>B: COMMIT
        R-->>U: « La bouteille a été déplacée » (occupation des deux étagères à jour)
    end
```

### Archivage d'une bouteille avec évaluation

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant R as routes_cave
    participant S as CaveService
    participant Bo as Bouteille
    participant Ev as Evaluation
    participant B as CaveRepository / SQLite

    U->>R: POST /bouteilles/{id}/archiver (note, commentaire, date)
    R->>R: convertit les champs (lire_nombre, lire_date)
    R->>S: archiver_bouteille(utilisateur, bouteille, note, commentaire, date)
    S->>B: BEGIN IMMEDIATE puis charger la cave de l'utilisateur
    S->>Bo: archiver(note, commentaire, date_sortie)
    alt déjà archivée
        Bo-->>S: ValueError « déjà archivée »
        S->>B: ROLLBACK
    else date de sortie avant la date d'ajout ou dans le futur
        Bo-->>S: ValueError « date de sortie incohérente » (rien n'a été modifié)
        S->>B: ROLLBACK
    else en stock, date cohérente
        Bo->>Ev: crée l'Evaluation (vérifie 0 ≤ note ≤ 20 et la longueur du commentaire)
        alt note ou commentaire invalide
            Ev-->>S: ValueError (rien n'a été modifié)
            S->>B: ROLLBACK
        else note valide
            Bo->>Bo: quitte l'étagère, statut ARCHIVEE, date de sortie
            S->>B: UPDATE bouteilles (statut, étagère NULL, date_sortie)
            S->>B: INSERT evaluations (bouteille, auteur, vin, note, commentaire)
            S->>B: COMMIT
        end
    end
    R-->>U: redirige avec le message de succès ou d'erreur
    Note over U,B: La note moyenne du vin est recalculée à chaque affichage<br/>(CatalogueService.note_moyenne, AVG SQL) : elle tient compte de la<br/>nouvelle note, sans autre mise à jour.
```

### Envoi d'un formulaire et protection CSRF

Chaque formulaire POST contient un champ caché `csrf`. Le serveur refuse tout envoi dont le jeton n'est pas celui de
la session, avant même d'exécuter la route (voir `macave/csrf.py`).

```mermaid
sequenceDiagram
    actor U as Navigateur
    participant R as routes (Flask)
    participant K as csrf.py
    participant S as Session (cookie signé)

    U->>R: GET /etageres (une consultation ne demande pas de jeton)
    R->>K: jeton_csrf() (appelé dans chaque formulaire du template)
    K->>S: crée un jeton aléatoire s'il n'y en a pas encore
    R-->>U: page HTML, chaque formulaire contient le champ caché csrf

    U->>K: POST /etageres (champs du formulaire + csrf), cookie de session
    K->>S: lit le jeton de la session
    alt jeton absent ou différent
        K-->>U: erreur 400 « Formulaire refusé » (la route n'est pas exécutée)
    else jeton identique
        K->>R: la route s'exécute normalement
        R-->>U: redirection ou page
    end
    Note over U,S: Un site pirate peut faire envoyer le cookie par le navigateur,<br/>mais il ne connaît pas le jeton : il ne peut pas fabriquer un formulaire valable.
```

## Modèle relationnel

Le schéma SQL complet (types, contraintes `CHECK`, `UNIQUE`, clés étrangères) est dans
[`macave/schema.sql`](../../macave/schema.sql).

```mermaid
erDiagram
    UTILISATEURS ||--|| CAVES : "possède"
    CAVES ||--o{ ETAGERES : "contient"
    CAVES ||--o{ BOUTEILLES : "détient"
    ETAGERES |o--o{ BOUTEILLES : "range (si en stock)"
    VINS ||--o{ BOUTEILLES : "est la référence de"
    BOUTEILLES ||--o| EVALUATIONS : "donne lieu à"
    UTILISATEURS ||--o{ EVALUATIONS : "écrit"
    VINS ||--o{ EVALUATIONS : "reçoit"

    UTILISATEURS {
        int id PK
        text identifiant UK "unique, sans tenir compte de la casse"
        text email UK "unique, sans tenir compte de la casse"
        text mot_de_passe_hash "sel et hachage PBKDF2"
    }
    CAVES {
        int id PK
        int utilisateur_id FK "unique : une cave par utilisateur"
    }
    ETAGERES {
        int id PK
        int cave_id FK
        text nom "unique dans une cave"
        int capacite_max "strictement positive"
    }
    VINS {
        int id PK
        text domaine
        text nom
        text type "rouge, blanc, rose, effervescent"
        int millesime
        text region
        text description
        text photo_etiquette
        text cle_identite UK "évite les doublons"
    }
    BOUTEILLES {
        int id PK
        int vin_id FK
        int cave_id FK
        int etagere_id FK "NULL si archivée"
        real prix_achat "positif ou nul"
        text date_ajout
        text statut "en_stock ou archivee"
        text date_sortie "NULL tant qu'elle est en stock"
    }
    EVALUATIONS {
        int id PK
        int bouteille_id FK "unique : une évaluation par dégustation"
        int auteur_id FK
        int vin_id FK
        real note "entre 0 et 20"
        text commentaire
        text date
    }
```

## Architecture en couches

```mermaid
flowchart TB
    nav["Navigateur<br/>(pages HTML, formulaires)"]
    subgraph web["Couche web (Flask)"]
        routes["routes_auth.py · routes_cave.py · routes_vins.py<br/>sessions, accès réservé, lecture des formulaires"]
        tpl["templates/ (Jinja2)"]
        form["formulaires.py<br/>conversion du texte des formulaires"]
        csrf["csrf.py<br/>jeton CSRF vérifié avant chaque envoi de formulaire"]
    end
    subgraph services["Services"]
        auth["AuthService"]
        cave["CaveService<br/>(une transaction par opération)"]
        cat["CatalogueService"]
        rech["recherche.py<br/>filtre et tri"]
    end
    subgraph metier["Couche métier (classes Python)"]
        classes["Utilisateur · CavePrivee · Etagere<br/>Vin · Bouteille · Evaluation<br/>règles R1 à R12"]
    end
    subgraph persistance["Persistance"]
        repos["UtilisateurRepository · CaveRepository · VinRepository<br/>(SQL avec le module sqlite3)"]
        sql[("SQLite<br/>schema.sql")]
    end

    nav --> csrf
    csrf --> routes
    routes --> tpl
    routes --> form
    routes --> auth
    routes --> cave
    routes --> cat
    routes --> rech
    auth --> classes
    cave --> classes
    cat --> classes
    auth --> repos
    cave --> repos
    cat --> repos
    repos --> sql
```

Les règles de gestion (capacité, déplacement, archivage, dates, identité d'un vin) sont portées par les classes
du métier, qui ne connaissent ni Flask ni SQLite : les tests de `tests/test_modele.py` les vérifient sans base ni requête HTTP.

La note moyenne d'un vin fait exception : elle porte sur les évaluations de tous les utilisateurs, alors qu'une cave ne
charge que les siennes. Elle est calculée par `CatalogueService.note_moyenne` (SQL `AVG`, via `VinRepository`), et testée
elle aussi sans requête HTTP (`tests/test_catalogue_service.py`).
