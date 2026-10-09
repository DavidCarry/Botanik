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

-- Les visages que la serre sait nommer.
--
-- Ce qui est garde n'est PAS une photo mais une empreinte : les 128
-- nombres que le modele tire d'un visage. On ne remonte pas d'une
-- empreinte au visage, et reconnaitre quelqu'un revient a comparer deux
-- series de nombres -- rien n'est reappris, jamais.
--
-- Plusieurs lignes par personne, et c'est voulu : un visage de face et
-- un de trois quarts se ressemblent moins qu'on ne croit, et la
-- reconnaissance retient la MEILLEURE des ressemblances.
CREATE TABLE IF NOT EXISTS visages (
    id        BIGSERIAL PRIMARY KEY,
    nom       TEXT        NOT NULL,
    empreinte BYTEA       NOT NULL,   -- 128 flottants, soit 512 octets
    origine   TEXT        NOT NULL,   -- d'ou vient cette reference
    cree_le   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_visages_nom ON visages (nom);

-- Ce que la serre fait quand elle voit quelqu'un.
--
-- Meme forme d'action que les regles de bornes -- allumer un actionneur,
-- afficher un texte -- parce que c'est la meme chose qui se declenche.
-- Seul le declencheur change : une personne devant la camera plutot
-- qu'une mesure qui passe une borne.
--
-- `sujet` est le nom d'une personne apprise, ou « quiconque » (n'importe
-- qui) ou « inconnu » (un visage qui ne correspond a aucune reference).
CREATE TABLE IF NOT EXISTS regles_visages (
    sujet      TEXT PRIMARY KEY,
    action     JSONB       NOT NULL,
    modifie_le TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ce que chaque afficheur montre, et s'il etait allume.
--
-- Un REGLAGE, et non un etat. Les actionneurs repartent tous a l'arret
-- au demarrage, par prudence : une pompe qui redemarrerait seule sur un
-- souvenir d'avant la coupure pourrait noyer la serre. Un ecran ne
-- risque rien, et le voir revenir noir apres chaque deploiement n'avait
-- rien de prudent -- c'etait seulement du reglage perdu.
CREATE TABLE IF NOT EXISTS afficheurs (
    actionneur TEXT PRIMARY KEY,
    contenu    JSONB       NOT NULL,
    allume     BOOLEAN     NOT NULL DEFAULT false,
    modifie_le TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A partir de quelle clarte la lumiere COMPTE dans le cumul du jour.
--
-- Le cumul se reglait en heures mais pas en pourcentage : on pouvait
-- demander douze heures de lumiere sans pouvoir dire douze heures de
-- QUOI. C'est ce chiffre-la.
--
-- Une seule ligne, et la contrainte s'en charge : `seul` ne peut valoir
-- que `true`, donc une seconde pose remplace la premiere au lieu
-- d'installer un reglage concurrent. Ce n'est pas un reglage par
-- capteur, c'est la definition de « eclaire » pour toute la serre, et
-- deux definitions a la fois n'auraient aucun sens.
--
-- Table VIDE = personne n'y a touche. Le defaut vient alors du code, ce
-- qui evite de semer une ligne au premier demarrage et de se demander
-- ensuite si elle a ete choisie ou heritee.
CREATE TABLE IF NOT EXISTS eclairement (
    seul       BOOLEAN PRIMARY KEY DEFAULT true CHECK (seul),
    mode       TEXT             NOT NULL DEFAULT 'ia'
                                CHECK (mode IN ('ia', 'manuel')),
    utile      DOUBLE PRECISION,
    modifie_le TIMESTAMPTZ      NOT NULL DEFAULT now()
);
"""

# Ce qui a change APRES coup sur une table d'`init.sql`, qu'une base deja
# installee ne reverra jamais autrement. On defait avant de reposer :
# rejouer ces ordres a chaque demarrage ne coute rien et ne casse rien.
MIGRATIONS = """
-- `commandes` date du temps ou le reseau decidait. Depuis, une action
-- a trois causes possibles : un clic, une borne franchie, ou une
-- personne reconnue. Sans cette reprise, la contrainte refuse les
-- ordres des regles -- et le journal resterait muet sur tout ce que la
-- serre fait d'elle-meme.
--
-- L'ORDRE COMPTE, et il a deja mordu : la contrainte tombe d'ABORD.
-- Reecrire les lignes avant de la lever les faisait refuser par
-- l'ancienne contrainte, l'ordre entier echouait, et les services qui
-- preparent le schema au demarrage ne demarraient plus du tout.
ALTER TABLE IF EXISTS commandes
    DROP CONSTRAINT IF EXISTS commandes_source_check;

-- Les lignes ecrites quand les deux causes automatiques n'en faisaient
-- qu'une sont versees aux seuils : les regles de visages n'existaient
-- pas encore quand elles ont ete enregistrees.
UPDATE commandes SET source = 'seuil' WHERE source = 'regle';

ALTER TABLE IF EXISTS commandes
    ADD CONSTRAINT commandes_source_check
    CHECK (source IN ('manuel', 'seuil', 'visage'));

-- `eclairement` est nee sans mode : sa clarte utile se saisissait a la
-- main, et seulement a la main. Elle se regle depuis comme les bornes
-- d'une regle, « ia » ou « manuel », d'ou la colonne qui s'ajoute -- et
-- la valeur qui cesse d'etre obligatoire, puisqu'en mode « ia » il n'y
-- en a pas.
ALTER TABLE IF EXISTS eclairement
    ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'ia';

-- Une ligne ecrite avant le mode portait forcement un chiffre tape a la
-- main : c'est du manuel, et le dire evite de l'effacer en silence.
UPDATE eclairement SET mode = 'manuel' WHERE utile IS NOT NULL;

-- La contrainte est posee a part, et non sur la colonne ajoutee : sur
-- une base neuve elle existe deja (voir TABLES), et `ADD COLUMN IF NOT
-- EXISTS` n'aurait alors rien pose du tout.
ALTER TABLE IF EXISTS eclairement
    DROP CONSTRAINT IF EXISTS eclairement_mode_check;

ALTER TABLE IF EXISTS eclairement
    ADD CONSTRAINT eclairement_mode_check CHECK (mode IN ('ia', 'manuel'));

ALTER TABLE IF EXISTS eclairement ALTER COLUMN utile DROP NOT NULL;
"""


def preparer(conn):
    with conn.cursor() as cur:
        cur.execute(TABLES)
        cur.execute(MIGRATIONS)
