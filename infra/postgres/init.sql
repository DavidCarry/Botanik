-- Schema de Botanik, joue automatiquement a la creation du volume.

-- Telemetrie : une ligne par mesure.
-- Format long : ajouter un capteur n'exige aucune migration.
CREATE TABLE mesures (
    id      BIGSERIAL PRIMARY KEY,
    ts      TIMESTAMPTZ      NOT NULL DEFAULT now(),
    capteur TEXT             NOT NULL,
    valeur  DOUBLE PRECISION NOT NULL,
    unite   TEXT
);

CREATE INDEX idx_mesures_ts         ON mesures (ts DESC);
CREATE INDEX idx_mesures_capteur_ts ON mesures (capteur, ts DESC);

-- Actions envoyees aux actionneurs, avec leur origine.
CREATE TABLE commandes (
    id         BIGSERIAL PRIMARY KEY,
    ts         TIMESTAMPTZ      NOT NULL DEFAULT now(),
    actionneur TEXT             NOT NULL,
    valeur     DOUBLE PRECISION NOT NULL,
    source     TEXT             NOT NULL
               CHECK (source IN ('manuel', 'ia', 'securite'))
);

CREATE INDEX idx_commandes_ts ON commandes (ts DESC);

-- Poids du reseau de neurones (exigence "openweight" du sujet).
-- poids : tableaux NumPy serialises. metadonnees : archi, hyperparametres, metriques.
CREATE TABLE modeles (
    id          BIGSERIAL PRIMARY KEY,
    nom         TEXT        NOT NULL,
    version     TEXT        NOT NULL,
    poids       BYTEA       NOT NULL,
    metadonnees JSONB,
    cree_le     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (nom, version)
);
