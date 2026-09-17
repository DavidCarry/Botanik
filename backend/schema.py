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

-- Ce que l'utilisateur a decide pour chaque grandeur : ou passent ses
-- bornes, et ce que la serre doit faire quand elles sont franchies.
--
-- C'est la SEULE source des actions depuis qu'on a retire les regles
-- ecrites en dur. Le reseau, lui, continue d'apprendre des seuils : une
-- borne en mode « ia » le suit, une borne en mode « manuel » ne bouge
-- plus, une borne « aucun » ignore ce cote.
CREATE TABLE IF NOT EXISTS regles (
    grandeur    TEXT PRIMARY KEY,
    mode_bas    TEXT NOT NULL DEFAULT 'ia'
                CHECK (mode_bas IN ('ia', 'manuel', 'aucun')),
    mode_haut   TEXT NOT NULL DEFAULT 'ia'
                CHECK (mode_haut IN ('ia', 'manuel', 'aucun')),
    valeur_bas  DOUBLE PRECISION,
    valeur_haut DOUBLE PRECISION,
    -- {"genre": "actionneur", "cible": "bipeur", "valeur": 1}
    -- {"genre": "ecran", "texte": "Reservoir vide"}   ou NULL
    action_bas  JSONB,
    action_haut JSONB,
    modifie_le  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

# Ce qui a change APRES coup sur une table d'`init.sql`, qu'une base deja
# installee ne reverra jamais autrement. On defait avant de reposer :
# rejouer ces ordres a chaque demarrage ne coute rien et ne casse rien.
MIGRATIONS = """
-- `commandes` date du temps ou le reseau decidait. Depuis, il n'y a plus
-- que deux sources : un clic, ou une regle de l'utilisateur. Sans cette
-- reprise, la contrainte refuse les ordres des regles -- et le journal
-- resterait muet sur tout ce que la serre fait d'elle-meme.
ALTER TABLE IF EXISTS commandes
    DROP CONSTRAINT IF EXISTS commandes_source_check;
ALTER TABLE IF EXISTS commandes
    ADD CONSTRAINT commandes_source_check
    CHECK (source IN ('manuel', 'regle'));
"""


def preparer(conn):
    with conn.cursor() as cur:
        cur.execute(TABLES)
        cur.execute(MIGRATIONS)
