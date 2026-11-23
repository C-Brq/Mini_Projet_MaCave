-- Schéma SQLite de MaCave, rejouable sans danger
-- L'occupation d'une étagère est calculée, pas stockée

CREATE TABLE IF NOT EXISTS utilisateurs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    -- « Alice » et « alice » : même compte
    identifiant       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email             TEXT NOT NULL UNIQUE COLLATE NOCASE,
    -- « sel$hash » (PBKDF2), jamais en clair
    mot_de_passe_hash TEXT NOT NULL
);

-- Une cave par utilisateur
CREATE TABLE IF NOT EXISTS caves (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    utilisateur_id INTEGER NOT NULL UNIQUE REFERENCES utilisateurs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS etageres (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    cave_id      INTEGER NOT NULL REFERENCES caves(id) ON DELETE CASCADE,
    nom          TEXT NOT NULL COLLATE NOCASE,
    capacite_max INTEGER NOT NULL CHECK (capacite_max > 0),
    -- R2 : noms uniques dans une cave, sans tenir compte de la casse
    UNIQUE (cave_id, nom)
);

-- Catalogue partagé
CREATE TABLE IF NOT EXISTS vins (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    domaine         TEXT NOT NULL,
    nom             TEXT NOT NULL,
    type            TEXT NOT NULL CHECK (type IN ('rouge', 'blanc', 'rose', 'effervescent')),
    millesime       INTEGER NOT NULL CHECK (millesime > 0),
    region          TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    photo_etiquette TEXT NOT NULL DEFAULT '',
    -- évite les doublons (voir Vin.cle_identite)
    cle_identite    TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS bouteilles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vin_id      INTEGER NOT NULL REFERENCES vins(id),
    cave_id     INTEGER NOT NULL REFERENCES caves(id) ON DELETE CASCADE,
    -- bloque la suppression d'une étagère non vide (R5)
    etagere_id  INTEGER REFERENCES etageres(id),
    prix_achat  REAL NOT NULL CHECK (prix_achat >= 0),
    date_ajout  TEXT NOT NULL,   -- AAAA-MM-JJ
    statut      TEXT NOT NULL CHECK (statut IN ('en_stock', 'archivee')),
    date_sortie TEXT,            -- seulement si archivée
    -- en stock : sur une étagère ; archivée : hors étagère, avec date de sortie
    CHECK (
        (statut = 'en_stock' AND etagere_id IS NOT NULL AND date_sortie IS NULL)
        OR (statut = 'archivee' AND etagere_id IS NULL AND date_sortie IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS evaluations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    -- une évaluation par dégustation
    bouteille_id INTEGER NOT NULL UNIQUE REFERENCES bouteilles(id) ON DELETE CASCADE,
    auteur_id    INTEGER NOT NULL REFERENCES utilisateurs(id),
    vin_id       INTEGER NOT NULL REFERENCES vins(id),
    note         REAL NOT NULL CHECK (note >= 0 AND note <= 20),
    commentaire  TEXT,
    date         TEXT NOT NULL   -- date et heure ISO
);
