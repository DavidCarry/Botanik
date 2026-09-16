"""Les tables qui se creent au demarrage.

`infra/postgres/init.sql` n'est joue qu'a la CREATION du volume Docker :
sur une base deja en place, il n'est plus jamais relu. Toute table
apparue apres la premiere installation doit donc se creer ici, sans quoi
un deploiement sur une Pi existante partirait avec un schema incomplet.

Un seul module s'en charge, pour qu'on sache ou regarder. `IF NOT EXISTS`
partout : l'appel est idempotent et peut etre fait par plusieurs services
au demarrage sans se marcher dessus.
"""

TABLES = """
CREATE TABLE IF NOT EXISTS utilisateurs (
    id          BIGSERIAL PRIMARY KEY,
    identifiant TEXT UNIQUE NOT NULL,
    empreinte   TEXT        NOT NULL,
    cree_le     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    jeton     TEXT PRIMARY KEY,
    compte_id BIGINT      NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    expire_le TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_expire ON sessions (expire_le);

-- Une ligne par episode : ouverte quand le probleme est detecte, fermee
-- quand il cesse. `fin` a NULL signifie donc « en cours », ce qui evite
-- d'entretenir un etat ailleurs.
CREATE TABLE IF NOT EXISTS alertes (
    id       BIGSERIAL PRIMARY KEY,
    grandeur TEXT        NOT NULL,
    cote     TEXT        NOT NULL CHECK (cote IN ('bas', 'haut')),
    debut    TIMESTAMPTZ NOT NULL DEFAULT now(),
    fin      TIMESTAMPTZ
);

-- Retrouver l'episode en cours d'une grandeur est l'operation la plus
-- frequente : une fois par message d'alerte.
CREATE INDEX IF NOT EXISTS idx_alertes_ouvertes
    ON alertes (grandeur) WHERE fin IS NULL;

CREATE INDEX IF NOT EXISTS idx_alertes_debut ON alertes (debut DESC);
"""


def preparer(conn):
    with conn.cursor() as cur:
        cur.execute(TABLES)
